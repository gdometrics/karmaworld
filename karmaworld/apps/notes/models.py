#!/usr/bin/env python
# -*- coding:utf8 -*-
# Copyright (C) 2012  FinalsClub Foundation

"""
    Models for the notes django app.
    Contains only the minimum for handling files and their representation
"""
import os
import time
import urllib
import logging
import datetime
import traceback

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files.storage import default_storage
from django.db.models import SET_NULL
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.text import slugify

import markdown
import django_filepicker
from taggit.managers import TaggableManager
from allauth.account.signals import user_logged_in

from karmaworld.apps.notes import sanitizer
from karmaworld.apps.users.models import UserProfile
from karmaworld.apps.users.models import NoteKarmaEvent
from karmaworld.apps.users.models import GenericKarmaEvent
from karmaworld.apps.notes.search import SearchIndex
from karmaworld.apps.courses.models import Course
from karmaworld.apps.licenses.models import License

from karmaworld.utils.filepicker import sign_fp_policy
from karmaworld.utils.filepicker import encode_fp_policy

from karmaworld.settings.manual_unique_together import auto_add_check_unique_together

FILEPICKER_API_KEY = os.environ['FILEPICKER_API_KEY']

ANONYMOUS_UPLOAD_URLS = 'anonymous_upload_urls'
KEYWORD_MTURK_THRESHOLD = 3

logger = logging.getLogger(__name__)
fs = FileSystemStorage(location=settings.MEDIA_ROOT)

# Dictionary for S3 upload headers
s3_upload_headers = {
    'Content-Type': 'text/html',
}

# This is a bit hacky, but nothing else works. Grabbed this from a proper
# file configured via S3 management console.
# https://github.com/FinalsClub/karmaworld/issues/273#issuecomment-32572169
all_read_xml_acl = '<?xml version="1.0" encoding="UTF-8"?>\n<AccessControlPolicy xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Owner><ID>710efc05767903a0eae5064bbc541f1c8e68f8f344fa809dc92682146b401d9c</ID><DisplayName>Andrew</DisplayName></Owner><AccessControlList><Grant><Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CanonicalUser"><ID>710efc05767903a0eae5064bbc541f1c8e68f8f344fa809dc92682146b401d9c</ID><DisplayName>Andrew</DisplayName></Grantee><Permission>READ</Permission></Grant><Grant><Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CanonicalUser"><ID>710efc05767903a0eae5064bbc541f1c8e68f8f344fa809dc92682146b401d9c</ID><DisplayName>Andrew</DisplayName></Grantee><Permission>WRITE</Permission></Grant><Grant><Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CanonicalUser"><ID>710efc05767903a0eae5064bbc541f1c8e68f8f344fa809dc92682146b401d9c</ID><DisplayName>Andrew</DisplayName></Grantee><Permission>READ_ACP</Permission></Grant><Grant><Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="CanonicalUser"><ID>710efc05767903a0eae5064bbc541f1c8e68f8f344fa809dc92682146b401d9c</ID><DisplayName>Andrew</DisplayName></Grantee><Permission>WRITE_ACP</Permission></Grant><Grant><Grantee xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="Group"><URI>http://acs.amazonaws.com/groups/global/AllUsers</URI></Grantee><Permission>READ</Permission></Grant></AccessControlList></AccessControlPolicy>'


class Document(models.Model):
    """
    An Abstract Base Class representing a document intended to be subclassed.
    """
    course          = models.ForeignKey(Course)
    tags            = TaggableManager(blank=True)
    name            = models.CharField(max_length=255, blank=True, null=True)
    slug            = models.SlugField(max_length=255, unique=True)

    LECTURE_NOTES = 'LECTURE_NOTES'
    STUDY_GUIDE = 'STUDY_GUIDE'
    SYLLABUS = 'SYLLABUS'
    ASSIGNMENT = 'ASSIGNMENT'
    OTHER = 'OTHER'
    NOTE_CATEGORIES = (
        (LECTURE_NOTES, 'Lecture Notes'),
        (STUDY_GUIDE, 'Study Guide'),
        (SYLLABUS, 'Syllabus'),
        (ASSIGNMENT, 'Assignment'),
        (OTHER, 'Other'),
    )
    EDITABLE_CATEGORIES = (LECTURE_NOTES,)

    category = models.CharField(max_length=50, choices=NOTE_CATEGORIES, blank=True, null=True)

    # license if different from default
    license         = models.ForeignKey(License, blank=True, null=True)

    # provide an upstream file link
    upstream_link   = models.URLField(max_length=1024, blank=True, null=True, unique=True)

    # metadata relevant to the Upload process
    user            = models.ForeignKey(User, blank=True, null=True, on_delete=SET_NULL)
    ip              = models.GenericIPAddressField(blank=True, null=True,
                        help_text=u"IP address of the uploader")
    uploaded_at     = models.DateTimeField(null=True, default=datetime.datetime.utcnow)


    # if True, NEVER show this file
    # WARNING: This may throw an error on migration
    is_hidden       = models.BooleanField(default=False)

    ###
    # Everything Filepicker, now in one small area

    # Allow pick (choose files), store (upload to S3), read (from FP repo),
    # stat (status of FP repo files) for 1 year (current time + 365 * 24 * 3600
    # seconds). Generated one time, at class definition upon import. So the
    # server will need to be rebooted at least one time each year or this will
    # go stale.
    fp_policy_json = '{{"expiry": {0}, "call": ["pick","store","read","stat"]}}'
    fp_policy_json = fp_policy_json.format(int(time.time() + 31536000))
    fp_policy      = encode_fp_policy(fp_policy_json)
    fp_signature   = sign_fp_policy(fp_policy)

    # Hack because mimetypes conflict with extensions, but there is no way to
    # disable mimetypes.
    # https://github.com/Ink/django-filepicker/issues/22
    django_filepicker.forms.FPFieldMixin.default_mimetypes = ''
    # Now let django-filepicker do the heavy lifting. Sort of. Look at all those
    # parameters!
    fp_file = django_filepicker.models.FPFileField(
                # FPFileField settings
                apikey=FILEPICKER_API_KEY,
                services='COMPUTER,DROPBOX,URL,GOOGLE_DRIVE,EVERNOTE,GMAIL,BOX,FACEBOOK,FLICKR,PICASA,IMAGE_SEARCH,WEBCAM,FTP',
                additional_params={
                    'data-fp-multiple': 'true', 
                    'data-fp-folders': 'true',
                    'data-fp-button-class':
                      'inline-button important add-note-btn',
                    'data-fp-button-text': 'Add Notes',
                    'data-fp-extensions':
                      '.pdf,.doc,.docx,.txt,.html,.rtf,.odt,.png,.jpg,.jpeg,.ppt,.pptx',
                    'data-fp-store-location': 'S3',
                    'data-fp-policy': fp_policy,
                    'data-fp-signature': fp_signature,
                    'type': 'filepicker',
                    'onchange': "got_file(event)",
                },
                # FileField settings
                null=True, blank=True,
                upload_to='nil', # field ignored because S3, but required.
                verbose_name='', # prevent a label from showing up
                )
    mimetype = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ['-uploaded_at']

    def _generate_unique_slug(self):
        """ generate a unique slug based on name and uploaded_at  """
        _slug = slugify(unicode(self.name))
        klass = self.__class__
        collision = klass.objects.filter(slug=_slug)
        if collision:
            _slug = u"{0}-{1}-{2}-{3}".format(
                    _slug, self.uploaded_at.month,
                    self.uploaded_at.day, self.uploaded_at.microsecond)
        self.slug = _slug

    def _get_fpf(self):
        """
        Memoized FilepickerFile getter. Returns FilepickerFile.
        """
        if not hasattr(self, 'cached_fpf'):
            # Fetch additional_params containing signature, etc
            aps = self.fp_file.field.additional_params
            self.cached_fpf = django_filepicker.utils.FilepickerFile(self.fp_file.name, aps)
        return self.cached_fpf

    def get_fp_url(self):
        """
        Returns the Filepicker URL for reading the upstream document.
        """
        fpf = self._get_fpf()
        # Return proper URL for reading
        return fpf.get_url()

    def get_file(self):
        """
        Downloads the file from filepicker.io and returns a Django File wrapper
        object.
        """
        # Fetch FilepickerFile
        fpf = self._get_fpf()
        # Return Django File
        return fpf.get_file()

    def save(self, *args, **kwargs):
        if self.name and not self.slug:
            self._generate_unique_slug()
        super(Document, self).save(*args, **kwargs)


class NoteManager(models.Manager):
    """ Handle restoring data. """
    def get_by_natural_key(self, fp_file, upstream_link):
        """
        Return a Note defined by its Filepicker and upstream URLs.
        """
        return self.get(fp_file=fp_file,upstream_link=upstream_link)


class Note(Document):
    """ 
    A django model representing an uploaded file and associated metadata.
    """
    objects = NoteManager()

    PDF_MIMETYPES = (
      'application/pdf',
      'application/vnd.ms-powerpoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    )

    # Cache the Google drive file link
    gdrive_url      = models.URLField(max_length=1024, blank=True, null=True, unique=True)

    # Generated by Google Drive but saved locally
    text            = models.TextField(blank=True, null=True)

    # Number of times this note has been flagged as abusive/spam.
    flags           = models.IntegerField(default=0,null=False)

    # Social media tracking
    tweeted         = models.BooleanField(default=False)
    thanks          = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('fp_file', 'upstream_link')
        ordering = ['-uploaded_at']

    def __unicode__(self):
        return u"Note at {0} (from {1}) ({2})".format(self.fp_file, self.upstream_link, self.id)

    def natural_key(self):
        """
        A Note is uniquely defined by both the Filepicker link and the upstream
        link. The Filepicker link should be unique by itself, but it may be
        null in the database, so the upstream link component should resolve
        those cases.
        """
        # gdrive_url might also fit the bill?
        return (self.fp_file, self.upstream_link)

    def get_relative_s3_path(self):
        """
        returns s3 path relative to the appropriate bucket.
        """
        # Note.slug will be unique and brought in from RawDocument or created
        # upon save() inside RawDocument.convert_to_note(). It makes for a good
        # filename and its pretty well guaranteed to be there.
        return 'html/{0}.html'.format(self.slug)

    def send_to_s3(self, html, do_save=True):
        """
        Push the given HTML up to S3 for this Note.
        Set do_save to False if the note will be saved outside this call.
        """
        # do nothing if HTML is empty.
        if not html or not len(html):
            return
        # upload the HTML file to static host if it is not already there
        filepath = self.get_relative_s3_path()
        if not default_storage.exists(filepath):
            # This is a pretty ugly hackified answer to some s3boto shortcomings
            # and some decent default settings chosen by django-storages.

            # Create the new key (key == filename in S3 bucket)
            newkey = default_storage.bucket.new_key(filepath)
            # Upload data!
            newkey.set_contents_from_string(html, headers=s3_upload_headers)
            if not newkey.exists():
                raise LookupError('Unable to find uploaded S3 document {0}'.format(str(newkey)))

            # set the permissions for everyone to read.
            newkey.set_xml_acl(all_read_xml_acl)

    def update_note_on_s3(self, html):
        # do nothing if HTML is empty.
        if not html or not len(html):
            return
        # if it's not already there then bail out
        filepath = self.get_relative_s3_path()
        if not default_storage.exists(filepath):
            logger.warn("Cannot update note on S3, it does not exist already: " + unicode(self))
            return

        key = default_storage.bucket.get_key(filepath)
        key.set_contents_from_string(html, headers=s3_upload_headers)
        key.set_xml_acl(all_read_xml_acl)

    def remaining_thanks_for_mturk(self):
        return KEYWORD_MTURK_THRESHOLD - self.thanks

    def total_thanks_for_mturk(self):
        return KEYWORD_MTURK_THRESHOLD

    def get_canonical_url(self):
        return "http://{0}{1}".format(
            Site.objects.get_current().domain,
            self.get_absolute_url())

    def get_absolute_url(self):
        """ Resolve note url, use 'note' route and slug if slug
            otherwise use note.id
        """
        if self.slug:
            # return a url ending in slug
            if self.course.school:
                return reverse('note_detail', args=[self.course.school.slug, self.course.slug, self.slug])
            else:
                return reverse('note_detail', args=[self.course.department.school.slug, self.course.slug, self.slug])
        else:
            # return a url ending in id
            return reverse('note_detail', args=[self.course.school.slug, self.course.slug, self.id])

    def get_absolute_keywords_url(self):
        """ Resolve note url, use 'note' route and slug if slug
            otherwise use note.id
        """
        if self.slug is not None:
            # return a url ending in slug
            if self.course.school:
                return reverse('note_keywords', args=[self.course.school.slug, self.course.slug, self.slug])
            else:
                return reverse('note_keywords', args=[self.course.department.school.slug, self.course.slug, self.slug])
        else:
            # return a url ending in id
            return reverse('note_keywords', args=[self.course.school.slug, self.course.slug, self.id])

    def get_absolute_quiz_url(self):
        """ Resolve note url, use 'note' route and slug if slug
            otherwise use note.id
        """
        if self.slug is not None:
            # return a url ending in slug
            if self.course.school:
                return reverse('note_quiz', args=[self.course.school.slug, self.course.slug, self.slug])
            else:
                return reverse('note_quiz', args=[self.course.department.school.slug, self.course.slug, self.slug])
        else:
            # return a url ending in id
            return reverse('note_quiz', args=[self.course.school.slug, self.course.slug, self.id])

    def _update_parent_updated_at(self):
        """ update the parent Course.updated_at model
            with the latest uploaded_at """
        self.course.updated_at = self.uploaded_at
        self.course.save()

    def save(self, *args, **kwargs):
        if self.uploaded_at and self.uploaded_at > self.course.updated_at:
            self._update_parent_updated_at()
        super(Note, self).save(*args, **kwargs)

    def has_markdown(self):
        return hasattr(self, "notemarkdown")

    def is_pdf(self):
        return self.mimetype in Note.PDF_MIMETYPES

    def is_editable(self):
        return self.category in Note.EDITABLE_CATEGORIES


    def allows_edit_by(self, user, cache={}):
        """
        Security policy for editing notes. Hand rolled for now.
        cache is a dictionary to return some calculated info pass-by-ref.
          (does nothing, maintained for consistency)
        Returns True if the user can edit the note.
        Checks if the user can tag and the note is editable.
        """
        # Of course the note must be editable in the first place.
        # If so, user must be able to tag note to edit it.
        return self.is_editable() and self.allows_tags_by(user)

    def allows_tags_by(self, user, cache={}):
        """
        Security policy for tagging notes. Hand rolled for now.
        cache is a dictionary to return some calculated info pass-by-ref.
        Returns True if the user can edit the note.
        Checks if the user can delete and there are enough points to tag.
        """
        # If the user cannot delete the note, the user cannot add tags.
        if not self.allows_delete_by(user, cache):
            return False
        # Staff can edit, no worries about points.
        if cache.has_key('staff') and cache['staff']:
            return True
        # Users must have 20 points to edit tags.
        if cache.has_key('profile'):
            # make sure to update points, caching is really just for passing
            # back in the call stack, not caching for long periods.
            cache['points'] = cache['profile'].get_points()
        return cache.has_key('points') and cache['points'] >= 20

    def allows_delete_by(self, user, cache={}):
        """
        Security policy for deleting notes. Hand rolled for now.
        cache is a dictionary to return some calculated info pass-by-ref
        Returns True if the user can delete the note.
        Checks if user is admin or owns the note.
        """
        # do not allow unauthenticated users access
        if hasattr(user, 'is_authenticated') and not user.is_authenticated():
            return False
        cache['user'] = user
        # ensure user is a UserProfile by contract.
        if not hasattr(user, 'has_staff_status'):
            # assume it's a regular User and try to resolve it
            user = UserProfile.objects.get(user_id=user.id)
        cache['profile'] = user
        # if the user is staff, the user can delete.
        cache['staff'] = False
        if user.has_staff_status():
            cache['staff'] = True
            return True
        # apparently some notes are un-owned. so, user is not the owner.
        if self.user is None:
            return False
        # pull user id for this note
        owner_id = self.user.id
        # Note owner may edit, others may not.
        return owner_id == user.get_id()

class NoteMarkdown(models.Model):
    note     = models.OneToOneField(Note, primary_key=True)
    markdown = models.TextField(blank=True, null=True)
    html     = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.markdown and not self.html:
            self.html = markdown.markdown(self.markdown)
        if self.note.is_editable():
            self.html = sanitizer.sanitize_html_to_editable(self.html)
        else:
            self.html = sanitizer.sanitize_html_preserve_formatting(self.html)

        super(NoteMarkdown, self).save(*args, **kwargs)

auto_add_check_unique_together(Note)


def update_note_counts(note_instance):
    try:
        # test if the course still exists, or if this is a cascade delete.
        note_instance.course
    except Course.DoesNotExist:
        # this is a cascade delete. there is no course to update
        pass
    else:
        # course exists
        note_instance.course.update_thank_count()
        note_instance.course.update_note_count()
        if note_instance.course.school:
            note_instance.course.school.update_note_count()
        elif note_instance.course.department.school:
            note_instance.course.department.school.update_note_count()

@receiver(pre_save, sender=Note, weak=False)
def note_pre_save_receiver(sender, **kwargs):
    """Stick an instance of the pre-save value of
    the given Note instance in the instances itself.
    This will be looked at in post_save."""
    if not 'instance' in kwargs:
        return

    try:
        kwargs['instance'].old_instance = Note.objects.get(id=kwargs['instance'].id)
    except ObjectDoesNotExist:
        pass

@receiver(post_save, sender=Note, weak=False)
def note_save_receiver(sender, **kwargs):
    if not 'instance' in kwargs:
        return
    note = kwargs['instance']


    update_note_counts(note)

    try:
        index = SearchIndex()
        if kwargs['created']:
            index.add_note(note)
        else:
            index.update_note(note, note.old_instance)
    except Exception:
        logger.error("Error with IndexDen:\n" + traceback.format_exc())


@receiver(post_delete, sender=Note, weak=False)
def note_delete_receiver(sender, **kwargs):
    if not 'instance' in kwargs:
        return
    note = kwargs['instance']

    # Update course and school counts of how
    # many notes they have
    update_note_counts(kwargs['instance'])

    # Remove document from search index
    try:
        index = SearchIndex()
        index.remove_note(note)
    except Exception:
        logger.error("Error with IndexDen:\n" + traceback.format_exc())

    if note.user:
        GenericKarmaEvent.create_event(note.user, note.name, GenericKarmaEvent.NOTE_DELETED)


class UserUploadMapping(models.Model):
    user = models.ForeignKey(User)
    fp_file = models.CharField(max_length=255)

    class Meta:
        unique_together = ('user', 'fp_file')


@receiver(user_logged_in, weak=True)
def find_orphan_notes(sender, **kwargs):
    user = kwargs['user']
    s = kwargs['request'].session
    uploaded_note_urls = s.get(ANONYMOUS_UPLOAD_URLS, [])
    for uploaded_note_url in uploaded_note_urls:
        try:
            note = Note.objects.get(fp_file=uploaded_note_url)
            note.user = user
            note.save()
            NoteKarmaEvent.create_event(user, note, NoteKarmaEvent.UPLOAD)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            mapping = UserUploadMapping.objects.create(fp_file=uploaded_note_url, user=user)
            mapping.save()

