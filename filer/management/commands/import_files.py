import os
from optparse import make_option

from django.core.management.base import BaseCommand, NoArgsCommand
from django.core.files import File as DjangoFile

from filer.models.foldermodels import Folder
from filer.models.filemodels import File
from filer.models.imagemodels import Image

from filer.settings import FILER_IS_PUBLIC_DEFAULT

class FileImporter(object):
    def __init__(self, * args, **kwargs):
        self.path = kwargs.get('path')
        self.verbosity = int(kwargs.get('verbosity', 1))
        self.file_created = 0
        self.image_created = 0
        self.folder_created = 0
    
    def import_file(self, file, folder):
        """
        Create a File or an Image into the given folder
        
        """
        try:
            iext = os.path.splitext(file.name)[1].lower()
        except:
            iext = ''
        if iext in ['.jpg', '.jpeg', '.png', '.gif']:
            obj, created = Image.objects.get_or_create(
                                original_filename=file.name,
                                file=file,
                                folder=folder,
                                is_public=FILER_IS_PUBLIC_DEFAULT)
            if created:
                self.image_created += 1
        else:
            obj, created = File.objects.get_or_create(
                                original_filename=file.name,
                                file=file,
                                folder=folder,
                                is_public=FILER_IS_PUBLIC_DEFAULT)
            if created:
                self.file_created += 1
        if self.verbosity >= 2:
            print u"file_created #%s / image_created #%s -- file : %s -- created : %s" % (self.file_created,
                                                        self.image_created,
                                                        obj, created)  
        return obj
    
    def get_or_create_folder(self, folder_names):
        """
        Gets or creates a Folder based the list of folder names in hierarchical 
        order (like breadcrumbs).
        
        get_or_create_folder(['root', 'subfolder', 'subsub folder'])
        
        creates the folders with correct parent relations and returns the 
        'subsub folder' instance.
        """
        if not len(folder_names):
            return None
        current_parent = None
        for folder_name in folder_names:
            current_parent, created = Folder.objects.get_or_create(name=folder_name, parent=current_parent)
            if created:
                self.folder_created += 1
                if self.verbosity >= 2:
                    print u"folder_created #%s folder : %s -- created : %s" % (self.folder_created,
                                                                               current_parent, created) 
        return current_parent
    
    def walker(self, path=None):
        """
        This method walk a directory structure and create the
        Folders and Files as they appear.
        """
        path = path or self.path
        # prevent trailing slashes and other inconsistencies on path.
        # cast to unicode so that os.walk returns path names in unicode
        # (prevents encoding/decoding errors)
        path = unicode(os.path.normpath(path))
        if self.verbosity >= 1:
            print u"Import the folders and files in %s" % path
        root_folder_name = os.path.basename(path)
        for root, dirs, files in os.walk(path):
            rel_folders = root.partition(path)[2].strip(os.path.sep).split(os.path.sep)
            while '' in rel_folders:
                rel_folders.remove('')
            folder_names = [root_folder_name] + rel_folders
            folder = self.get_or_create_folder(folder_names)
            for file in files:
                dj_file = DjangoFile(open(os.path.join(root, file)),
                                     name=file)
                self.import_file(file=dj_file, folder=folder)
        if self.verbosity >= 1:
            print u"folder_created #%s / file_created #%s / image_created #%s "% (self.folder_created,
                                                                                 self.file_created,
                                                                                 self.image_created)

class Command(NoArgsCommand):
    option_list = BaseCommand.option_list + (
        make_option('--path',
            action='store',
            dest='path',
            default=False,
            help='Import files located in the path into django-filer'),
        )

    def handle_noargs(self, **options):
        file_importer = FileImporter(**options)
        file_importer.walker()
