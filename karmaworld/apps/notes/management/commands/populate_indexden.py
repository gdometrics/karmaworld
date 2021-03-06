#!/usr/bin/env python
# -*- coding:utf8 -*-
# Copyright (C) 2013  FinalsClub Foundation

import traceback
from django.core.management.base import BaseCommand
from karmaworld.apps.notes.models import Note
from karmaworld.apps.notes.search import SearchIndex

class Command(BaseCommand):
    args = 'none'
    help = "Populate the search index in IndexDen with all the notes" \
           "in the database. Will not clear the index beforehand, so notes" \
           "in the index that are not overwritten will still be around."

    def handle(self, *args, **kwargs):
        index = SearchIndex()
        for note in Note.objects.iterator():
            try:
                print "Indexing {n}".format(n=note)
                index.add_note(note)
            except Exception, e:
                traceback.print_exc()
                continue

