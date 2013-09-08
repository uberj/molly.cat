import glob
import os
import simplejson as json
import requests
import pprint
import Image

from settings import imgur_client_ID

pp = pprint.PrettyPrinter(indent=4)

GALLERY_DIR = os.path.abspath('./media/img/gallery/') + '/'
REL_GALLERY_DIR = '/img/gallery/'
FILE_TYPES = ['jpg', 'JPG', 'jpeg', 'JPEG', 'png', 'PNG', 'gif', 'GIF']
THUMB_PREFIX = 'THUMB_'
PREVIEW_IMGS_NUM = 3

imgur_headers = {'Authorization': 'Client-ID {0}'.format(imgur_client_ID)}
ALBUM_URL = "https://api.imgur.com/3/album/{0}/"
ALBUM_CACHE = {}

TS = 'm'  # THUMB_SIZE_LETTER  (see http://api.imgur.com/models/image)

MAX_WIDTH = 400
MAX_HEIGHT = 600


class Gallery(object):
    def __init__(self):
        self.albums = {}

    def calc_thumb(self, src):
        for ft in FILE_TYPES:
            if src.endswith(ft):
                return src.replace('.' + ft, TS + '.' + ft)
        raise Exception("Unknown filetype for {0}".format(src))

    def get_imgur_album(self, album_id):
        global ALBUM_CACHE
        if album_id not in ALBUM_CACHE:
            response = requests.get(
                ALBUM_URL.format(album_id), headers=imgur_headers
            )
            ALBUM_CACHE[album_id] = json.loads(response.content)
        return ALBUM_CACHE[album_id]

    def calc_thumb_xy(self, *args):
        def refactor(*args):
            return map(lambda d: int(d * 0.9), args)

        def within_max(width, height):
            if width > MAX_WIDTH:
                return False
            if height > MAX_HEIGHT:
                return False
            return True

        while not within_max(*args):
            args = refactor(*args)

        return args

    def make_image(self, image):
        width = image['width']
        height = image['height']
        thumb_width, thumb_height = self.calc_thumb_xy(width, height)
        return {
            'thumb_src': self.calc_thumb(image['link']),
            'thumb_width': thumb_width,
            'thumb_height': thumb_height,

            'src': image['link'],
            'width': width,
            'height': height,
        }

    def get_imgur_album_images(self, page):
        if 'album-id' not in page.meta:
            raise Exception("No album id for {0}".format(page.meta['title']))
        return map(
            self.make_image,
            self.get_imgur_album(page.meta['album-id'])['data']['images']
        )

    def calc_img_hw(self, path):
        image = Image.open(path.replace(REL_GALLERY_DIR, GALLERY_DIR))
        return image.size[0], image.size[1]

    def get_images(self, ctx, page):
        """
        Wok page.template.pre hook
        Get all images in the album as relative paths
        Binds srcs and thumb_srcs to template
        """
        is_imgur = 'source' in page.meta and page.meta['source'] == 'imgur'
        if 'type' in page.meta and page.meta['type'] == 'album':
            album = page.meta
            images = []
            if is_imgur:
                pp.pprint(page.meta)
                # bind to template via json
                images = self.get_imgur_album_images(page)
                self.albums[album['slug']] = images
            else:
                # get paths of all of the images in the album
                srcs = []
                # get absolute paths of images in album for each file type
                for file_type in FILE_TYPES:
                    imgs = glob.glob(
                        GALLERY_DIR + album['slug'] + '/*.' + file_type
                    )

                    for img in imgs:
                        img_rel_path = (
                            REL_GALLERY_DIR +
                            album['slug'] + '/' + img.split('/')[-1]
                        )
                        srcs.append(img_rel_path)

                # split full srcs and thumb srcs from srcs into two lists
                images = []
                thumb_srcs = filter(
                    lambda src: src.split('/')[-1].startswith(THUMB_PREFIX),
                    srcs
                )
                for thumb_src in thumb_srcs:
                    src = thumb_src.replace(THUMB_PREFIX, '')
                    thumb_width, thumb_height = self.calc_img_hw(thumb_src)
                    width, height = self.calc_img_hw(src)
                    images.append({
                        'thumb_src': thumb_src,
                        'thumb_width': thumb_width,
                        'thumb_height': thumb_height,

                        'src': src,
                        'width': width,
                        'height': height,
                    })
                self.albums[album['slug']] = images

    def set_images(self, ctx, page, template_vars):
        album = page.meta
        if 'type' in page.meta and page.meta['type'] == 'album':
            template_vars['site']['images'] = json.dumps(
                self.albums[album['slug']]
            )

    def get_albums(self, ctx, page, templ_vars):
        """
        Wok page.template.pre hook
        Load several preview images into each album
        """
        if 'type' in page.meta and page.meta['type'] == 'index':
            album_pages = sorted(
                templ_vars['site']['categories']['gallery'],
                key=lambda album: album['datetime']
            )
            albums = {}
            for album_page in album_pages:
                image_list = []
                images = map(
                    lambda i: i['thumb_src'],
                    self.albums[album_page['slug']]
                )
                image_list += images[:PREVIEW_IMGS_NUM]
                albums[album_page['slug']] = image_list
            templ_vars['site']['albums'] = albums
