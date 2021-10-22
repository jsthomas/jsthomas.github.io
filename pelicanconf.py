#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'Joe Thomas'
SITENAME = u'Joe Thomas'
SITEURL = ''

PATH = 'content'

TIMEZONE = 'US/Eastern'

DEFAULT_LANG = u'en'

THEME = './themes/blue-penguin'

PLUGIN_PATHS = ['./plugins']
PLUGINS = ['render_math', 'better_figures_and_images']

READERS = {"html": None}

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('Pelican', 'http://getpelican.com/'),
         ('Python.org', 'http://python.org/'),
         ('Jinja2', 'http://jinja.pocoo.org/'),
         ('You can modify those links in your config file', '#'),)

# Social widget
SOCIAL = (('You can add links in your config file', '#'),
          ('Another social link', '#'),)

DEFAULT_PAGINATION = 10

STATIC_PATHS = ['images', 'docs', 'static']

SHOW_ARTICLE_AUTHOR = False
DISPLAY_FOOTER = False
DISPLAY_HOME = False

# provided as examples, they make ‘clean’ urls. used by MENU_INTERNAL_PAGES.
TAGS_URL           = 'tags'
TAGS_SAVE_AS       = 'tags/index.html'
AUTHORS_URL        = 'authors'
AUTHORS_SAVE_AS    = 'authors/index.html'
CATEGORIES_URL     = 'categories'
CATEGORIES_SAVE_AS = 'categories/index.html'
ARCHIVES_URL       = 'blog'
ARCHIVES_SAVE_AS   = 'blog/index.html'

# use those if you want pelican standard pages to appear in your menu
MENU_INTERNAL_PAGES = (
    ('Blog', ARCHIVES_URL, ARCHIVES_SAVE_AS),
)

# additional menu items
MENUITEMS = (
)

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
