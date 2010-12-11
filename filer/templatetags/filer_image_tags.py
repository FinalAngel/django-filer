from django.template import Library
import math
import re

import posixpath
from easy_thumbnails.templatetags.thumbnail import thumbnail, ThumbnailNode
from easy_thumbnails.files import ThumbnailFile
from filer import settings as filer_settings
from filer.utils.wrapper import ObjectWrapper
from django.utils import html

RE_SIZE = re.compile(r'(\d+)x(\d+)$')

register = Library()

def _recalculate_size(size, index, divisor=0, padding=0, keep_aspect_ratio=False):
    new_one = size[index]
    if divisor:
        new_one = new_one / float(divisor)
    if padding:
        new_one = new_one - padding
    if keep_aspect_ratio:
        new_two = int(float(new_one)*float(size[int(not index)])/size[index])
    else:
        new_two = int(size[int(not index)])
    
    new_one = int(new_one)
    if index:
        return (new_two, new_one)
    return new_one, new_two


def _resize(original_size, index, divisor=0, padding=0, keep_aspect_ratio=False):
    if isinstance(original_size, basestring):
        m = RE_SIZE.match(original_size)
        if m:
            original_size = (int(m.group(1)), int(m.group(2)))
        else:
            return original_size
    else:
        try:
            original_size = ( int(original_size[0]), int(original_size[1]) )
        except (TypeError, ValueError):
            return original_size
    try:
        padding = int(padding)
        divisor = int(divisor)
    except (TypeError, ValueError):
        return original_size
    # Re-calculate size
    new_x, new_y = _recalculate_size(original_size, index, divisor=divisor, 
                                     padding=padding, 
                                     keep_aspect_ratio=keep_aspect_ratio)
    return (new_x, new_y)

def extra_padding_x(original_size, padding):
    """
    Reduce the width of `original_size` by `padding`
    """
    return _resize(original_size, 0, padding=padding)
extra_padding_x = register.filter(extra_padding_x)

def extra_padding_x_keep_ratio(original_size, padding):
    """
    Reduce the width of `original_size` by `padding`, maintaining the aspect
    ratio.
    """
    return _resize(original_size, 0, padding=padding, keep_aspect_ratio=True)
extra_padding_x_keep_ratio = register.filter(extra_padding_x_keep_ratio)


def extra_padding_y(original_size, padding):
    """
    Reduce the height of `original_size` by `padding`
    """
    return _resize(original_size, 1, padding=padding)
extra_padding_y = register.filter(extra_padding_y)

def extra_padding_y_keep_ratio(original_size, padding):
    """
    Reduce the height of `original_size` by `padding`, maintaining the aspect
    ratio.
    """
    return _resize(original_size, 1, padding=padding, keep_aspect_ratio=True)
extra_padding_y_keep_ratio = register.filter(extra_padding_y_keep_ratio)

def divide_x_by(original_size, divisor):
    return _resize(original_size, 0, divisor=divisor)
devide_x_by = register.filter(divide_x_by)

def divide_y_by(original_size, divisor):
    return _resize(original_size, 1, divisor=divisor)
devide_y_by = register.filter(divide_y_by)

def divide_xy_by(original_size, divisor):
    size = divide_x_by(original_size, divisor=divisor)
    size = divide_y_by(size, divisor=divisor)
    return size
divide_xy_by = register.filter(divide_xy_by)


class WrapPrivateThumbnailFile(ObjectWrapper):
    def __init__(self, oInstance, filerFileId):
        ObjectWrapper.__init__(self, oInstance)
        thumbfile = posixpath.basename(oInstance.url)
        urlbase = filer_settings.FILER_PRIVATEMEDIA_URL
        self.newUrl = posixpath.normpath(posixpath.join(urlbase, "thumb", ("%04d" % filerFileId), thumbfile))

    @property
    def url(self):
        return self.newUrl

class WrapThumbnailNode(ObjectWrapper):
    def __init__(self, oInstance):
        ObjectWrapper.__init__(self, oInstance)

    def render(self, context):
        print "WrapThumbnailNode.render"
        # use a fake variable to always get a Thumbnail object in context
        fakevar = False
        if self.context_name == None:
            self.context_name = '__tmp__context__var__'
            fakevar = True
        thumb_url = ThumbnailNode.render(self, context)
        thumbnailer = context[self.context_name]
        if fakevar:
            if thumbnailer != '': # Assume thumbnailer is a File
                thumb_url = html.escape(thumbnailer.url)
            context[self.context_name] = ''
            self.context_name = None

        if thumbnailer == '': return thumb_url
        try:
            source = self.source_var.resolve(context)
        except VariableDoesNotExist:
            return thumb_url

        if not hasattr(source, "is_public"): return thumb_url
        if source.is_public: return thumb_url

        wfile = WrapPrivateThumbnailFile(thumbnailer, source.id)
        if fakevar:
            thumb_url = html.escape(wfile.url)
        else:
            context[self.context_name] = wfile

        return thumb_url

def filerthumbnail(parser, token):
    node = thumbnail(parser, token)
    return WrapThumbnailNode(node)

register.tag(filerthumbnail)