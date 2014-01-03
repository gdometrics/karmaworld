#!/usr/bin/env python
# -*- coding:utf8 -*-
# Copyright (C) 2013  FinalsClub Foundation
import time

import indextank.client as itc
import karmaworld.secret.indexden as secret

import logging

logger = logging.getLogger(__name__)

api_client = itc.ApiClient(secret.PRIVATE_URL)
if not api_client.get_index(secret.INDEX).exists():
    api_client.create_index(secret.INDEX, {'public_search': False})

index = api_client.get_index(secret.INDEX)

while not index.has_started():
    time.sleep(0.5)

def note_to_dict(note):
    d = {
        'name': note.name,
        'text': note.text
    }

    if note.tags.exists():
        d['tags'] = ' '.join([str(tag) for tag in note.tags.all()])

    if note.course:
        d['course_id'] = note.course.id

    return d

def add_document(note):
    if note.text:
        index.add_document(note.id, note_to_dict(note))
    else:
        logger.warn("Note {n} has no text, will not add to IndexDen".format(n=note))

def remove_document(note):
    index.delete_document(note.id)

def search(query, course_id=None):
    """Returns note IDs matching the given query,
    filtered by course ID if given"""
    if course_id:
        real_query = '("%s" OR name:"%s") AND course_id:%s' % (query, query, course_id)
    else:
        real_query = '"%s" OR name:"%s"' % (query, query)

    raw_results = index.search(real_query, snippet_fields=['text'])

    results = {r['docid']: r['snippet_text'] for r in raw_results['results']}

    return results