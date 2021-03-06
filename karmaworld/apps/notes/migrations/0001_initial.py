# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ('courses', '0001_initial'),
    )

    def forwards(self, orm):
        # Adding model 'Note'
        db.create_table('notes_note', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['courses.Course'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255, null=True)),
            ('ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True, blank=True)),
            ('uploaded_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow, null=True)),
            ('is_hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('fp_file', self.gf('django_filepicker.models.FPFileField')(max_length=100, null=True, blank=True)),
            ('mimetype', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('file_type', self.gf('django.db.models.fields.CharField')(default='???', max_length=15, null=True, blank=True)),
            ('pdf_file', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('note_file', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('embed_url', self.gf('django.db.models.fields.URLField')(max_length=1024, null=True, blank=True)),
            ('download_url', self.gf('django.db.models.fields.URLField')(max_length=1024, null=True, blank=True)),
            ('html', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('text', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('year', self.gf('django.db.models.fields.IntegerField')(default=2013, null=True, blank=True)),
            ('desc', self.gf('django.db.models.fields.TextField')(max_length=511, null=True, blank=True)),
            ('is_flagged', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_moderated', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('notes', ['Note'])

        # Adding model 'DriveAuth'
        db.create_table('notes_driveauth', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(default=u'admin@karmanotes.org', max_length=75)),
            ('credentials', self.gf('django.db.models.fields.TextField')()),
            ('stored_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('notes', ['DriveAuth'])


    def backwards(self, orm):
        # Deleting model 'Note'
        db.delete_table('notes_note')

        # Deleting model 'DriveAuth'
        db.delete_table('notes_driveauth')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'courses.course': {
            'Meta': {'ordering': "['-file_count', 'school', 'name']", 'object_name': 'Course'},
            'academic_year': ('django.db.models.fields.IntegerField', [], {'default': '2013', 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'max_length': '511', 'null': 'True', 'blank': 'True'}),
            'file_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructor_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'instructor_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'school': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['courses.School']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '150', 'null': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '511', 'null': 'True', 'blank': 'True'})
        },
        'courses.school': {
            'Meta': {'ordering': "['-file_count', '-priority', 'name']", 'object_name': 'School'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'facebook_id': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'file_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'priority': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '150', 'null': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '511', 'blank': 'True'}),
            'usde_id': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'notes.driveauth': {
            'Meta': {'object_name': 'DriveAuth'},
            'credentials': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'default': "u'admin@karmanotes.org'", 'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stored_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'notes.note': {
            'Meta': {'ordering': "['-uploaded_at']", 'object_name': 'Note'},
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['courses.Course']"}),
            'desc': ('django.db.models.fields.TextField', [], {'max_length': '511', 'null': 'True', 'blank': 'True'}),
            'download_url': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'embed_url': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'file_type': ('django.db.models.fields.CharField', [], {'default': "'???'", 'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'fp_file': ('django_filepicker.models.FPFileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'is_flagged': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mimetype': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'note_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'pdf_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255', 'null': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow', 'null': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'default': '2013', 'null': 'True', 'blank': 'True'})
        },
        'taggit.tag': {
            'Meta': {'ordering': "['namespace', 'name']", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'namespace': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['notes']
