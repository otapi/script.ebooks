# -*- coding: utf-8 -*-
import sys
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json

# Import the common settings
from resources.lib.settings import Settings
from resources.lib.settings import log
from resources.lib.settings import os_path_join

from resources.lib.textviewer import TextViewer
from resources.lib.ebook import EBookBase
from resources.lib.database import EbooksDB
from resources.lib.opds import Opds

ADDON = xbmcaddon.Addon(id='script.ebooks')
FANART = ADDON.getAddonInfo('fanart')


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    shelves = []

    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

        self.tmpdestination = Settings.getTempLocation()
        self.coverCache = Settings.getCoverCacheLocation()

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    def rootMenu(self):
        # Get the setting for the OPDS and ebook directory
        rootOpds = Settings.getOPDSLocation()
        eBookFolder = Settings.getEbookFolder()

        # If neither of OPDS and local folder set
        if rootOpds in [None, ""] and eBookFolder in [None, ""]:
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32034))
            return
        

        # If OPDS is not being used then just use the directory details
        if rootOpds in [None, ""]:
            self.showEbooksDirectory()
            return

        

        # If OPDS is enabled and there is no local folder set, then just use OPDS
        if eBookFolder in [None, ""]:
            self.opdsRootMenu()
            return

        # Both OPDS and local directory is enabled, so give the user the choice
        url = self._build_url({'mode': 'directory', 'directory': ' '})
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32005), iconImage='DefaultFolder.png')
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        opds = Opds()
        iconImage = opds.getRootImage()
        opdsTitle = opds.getRootTitle()
        del opds
        url = self._build_url({'mode': 'opds', 'href': ' '})
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32023), iconImage=iconImage)
        li.setProperty("Fanart_Image", FANART)
        li.setInfo('video', {'Plot': "[B]%s[/B]" % opdsTitle})
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def opdsRootMenu(self):
        log("EBooksPlugin: Getting OPDS Root Menu")
        opds = Opds()
        iconImage = opds.getRootImage()
        menuContents = opds.getRoootMenuContents()
        menuTitle = opds.getRootTitle()
        del opds

        for title in menuContents:
            url = self._build_url({'mode': 'opds2', 'href': menuContents[title]})
            li = xbmcgui.ListItem(title, iconImage=iconImage)
            li.setProperty("Fanart_Image", FANART)
            li.setInfo('video', {'Plot': "[B]%s[/B]" % menuTitle})
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def opdsBookListing(self, href):
        log("EBooksPlugin: Getting OPDS Book Listing for %s" % href)

        opds = Opds()
        contentList = opds.getList(href)
        contentTitle = opds.getRootTitle()

        if opds.isBookListContent():
            # Now display the book list
            self._showEbooks(contentList)
        else:
            for entry in contentList:
                url = self._build_url({'mode': 'opds2', 'href': entry['link']})
                li = xbmcgui.ListItem(entry['title'], iconImage=opds.getRootImage())
                li.setProperty("Fanart_Image", FANART)
                li.setInfo('video', {'Plot': "[B]%s[/B]" % contentTitle})
                li.addContextMenuItems([], replaceItems=True)
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

            xbmcplugin.endOfDirectory(self.addon_handle)

        del opds

    # Show all the EBooks that are in the eBook directory
    def showEbooksDirectory(self, directory=''):
        log("EBooksPlugin: Showing eBooks for directory %s" % str(directory))

        # Get the setting for the ebook directory
        eBookFolder = Settings.getEbookFolder()

        if eBookFolder in [None, ""]:
            # Prompt the user to set the eBooks Folder
            eBookFolder = xbmcgui.Dialog().browseSingle(0, ADDON.getLocalizedString(32005), 'files')

            # Check to make sure the directory is set now
            if eBookFolder in [None, ""]:
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32006))
                return

            # Save the directory in settings for future use
            log("EBooksPlugin: Setting eBooks folder to %s" % eBookFolder)
            Settings.setEbookFolder(eBookFolder)

        # We may be looking at a subdirectory
        if directory.strip() not in [None, ""]:
            eBookFolder = directory

        dirs, files = xbmcvfs.listdir(eBookFolder)
        dirs.sort()
        files.sort()

        # For each directory list allow the user to navigate into it
        for adir in dirs:
            if adir.startswith('.'):
                continue

            log("EBooksPlugin: Adding directory %s" % adir)

            nextDir = os_path_join(eBookFolder, adir)
            displayName = "[%s]" % adir

            try:
                displayName = "[%s]" % adir.encode("utf-8")
            except:
                displayName = "[%s]" % adir
            try:
                nextDir = nextDir.encode("utf-8")
            except:
                pass

            # Check if there is a folder image in the directory
            folderImage = 'DefaultFolder.png'
            fanartImage = FANART
            subdirs, filesInDir = xbmcvfs.listdir(nextDir)
            for fileInDir in filesInDir:
                if fileInDir.lower() in ['folder.jpg', 'cover.jpg', 'folder.png', 'cover.png']:
                    folderImage = os_path_join(nextDir, fileInDir)
                elif fileInDir.lower() in ['fanart.jpg', 'fanart.png']:
                    fanartImage = os_path_join(nextDir, fileInDir)

            url = self._build_url({'mode': 'directory', 'directory': nextDir})
            li = xbmcgui.ListItem(displayName, iconImage=folderImage)
            li.setProperty("Fanart_Image", fanartImage)
            plotDisplay = "[B]%s[/B]" % adir
            li.setInfo('video', {'Plot': plotDisplay})
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Now list all of the books
        for eBookFile in files:
            log("EBooksPlugin: Processing file %s" % eBookFile)
            # Check to ensure that this is an eBook
            if not Settings.isEbookFormat(eBookFile):
                log("EBooksPlugin: Skipping non ebook file: %s" % eBookFile)
                continue

            fullpath = os_path_join(eBookFolder, eBookFile)

            # Check in the database to see if this book is already recorded
            bookDB = EbooksDB()
            bookDetails = bookDB.getBookDetails(fullpath)

            title = ""
            author = ""
            description = ""
            isRead = False
            if bookDetails in [None, ""]:
                # Need the details of this book
                # Get the details of this book
                eBook = EBookBase.createEBookObject(fullpath)
                title = eBook.getTitle()
                author = eBook.getAuthor()
                description = eBook.getDescription()
                eBook.tidyUp()
                del eBook

                # Add this book to the list
                bookDB.addBook(fullpath, title, author, description)
            else:
                isRead = bookDetails['complete']
                title = bookDetails['title']
                author = bookDetails['author']
                description = bookDetails['description']
            del bookDB

            displayString = eBookFile
            try:
                displayString = title.encode("utf-8")
            except:
                displayString = title
            if author not in [None, ""]:
                try:
                    author = author.encode("utf-8")
                except:
                    pass
                try:
                    displayString = "%s - %s" % (author, displayString)
                except:
                    pass
            try:
                # With some text, logging is causing issues
                log("EBookBase: Display title is %s for %s" % (displayString, fullpath))
            except:
                pass

            if isRead:
                try:
                    displayString = '* %s' % displayString
                except:
                    log("EBookBase: Unable to mark as read")

            coverTargetName = EBookBase.getCoverImage(fullpath, eBookFile)
            if coverTargetName in [None, ""]:
                coverTargetName = Settings.getFallbackCoverImage()

            try:
                fullpath = fullpath.encode("utf-8")
            except:
                pass

            if coverTargetName not in [None, ""]:
                try:
                    coverTargetName = coverTargetName.encode("utf-8")
                except:
                    pass

            url = self._build_url({'mode': 'chapters', 'filename': fullpath, 'cover': coverTargetName})
            li = xbmcgui.ListItem(displayString, iconImage=coverTargetName)
            li.setProperty("Fanart_Image", EBookBase.getFanArt(fullpath))
            if description not in [None, ""]:
                li.setInfo('video', {'Plot': description})
            li.addContextMenuItems(self._getBookContextMenu(fullpath, "bookid"), replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Show all the EBooks that are in the eBook directory
    def _showEbooks(self, books):
        # List all of the books
        for bookDetails in books:
            log("EBooksPlugin: Processing title: %s, author: %s, link: %s, cover: %s" % (bookDetails['title'], bookDetails['author'], bookDetails['link'], bookDetails['cover']))

            # Check in the database to see if this book is already recorded
            bookDB = EbooksDB()
            dbBookDetails = bookDB.getBookDetails(bookDetails['link'])

            isRead = False
            if dbBookDetails in [None, ""]:
                # Add this book to the list
                bookDB.addBook(bookDetails['link'], bookDetails['title'], bookDetails['author'], bookDetails['description'])
            else:
                isRead = dbBookDetails['complete']

            del bookDB

            displayString = bookDetails['title']
            if bookDetails['author'] not in [None, ""]:
                displayString = "%s - %s" % (bookDetails['author'], displayString)
            log("EBookBase: Display title is %s for %s" % (displayString, bookDetails['link']))

            if isRead:
                displayString = '* %s' % displayString

            coverTargetName = bookDetails['cover']
            if coverTargetName in [None, ""]:
                coverTargetName = Settings.getFallbackCoverImage()

            url = self._build_url({'mode': 'chapters', 'filename': bookDetails['link'], 'cover': coverTargetName})
            li = xbmcgui.ListItem(displayString, iconImage=coverTargetName, thumbnailImage=coverTargetName)
            li.setProperty("Fanart_Image", FANART)
            if bookDetails['description'] not in [None, ""]:
                li.setInfo('video', {'Plot': bookDetails['description']})
            li.addContextMenuItems(self._getBookContextMenu(bookDetails['link'], "bookid"), replaceItems=False)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def listChapters(self, fullpath, defaultImage):
        log("EBooksPlugin: Listing chapters for %s" % fullpath)

        # Get the current chapter that has been read from the database
        readChapter = None
        readAll = False
        bookDB = EbooksDB()
        bookDetails = bookDB.getBookDetails(fullpath)
        del bookDB

        bookAuthorAndTitle = ""
        if bookDetails is not None:
            readChapter = bookDetails['readchapter']
            readAll = bookDetails['complete']
            # Create the author/title combination
            bookAuthorAndTitle = "[B]%s[/B]\n[I]%s[/I]" % (bookDetails['title'], bookDetails['author'])

        eBook = EBookBase.createEBookObject(fullpath)
        # Get the chapters for this book
        chapters = self._getChapters(fullpath, eBook)

        if bookAuthorAndTitle in [None, ""]:
            bookAuthorAndTitle = "[B]%s[/B]\n[I]%s[/I]" % (eBook.getTitle(), eBook.getAuthor())

        eBook.tidyUp()
        del eBook

        foundMatchedReadChapter = False
        # Add all the chapters to the display
        for chapter in chapters:
            url = self._build_url({'mode': 'readChapter', 'filename': chapter['filename'], 'title': chapter['title'], 'link': chapter['link'], 'firstChapter': chapter['firstChapter'], 'lastChapter': chapter['lastChapter']})

            # Check if we have already reached this chapter, if so, and the new chapter does not
            # point to the same chapter, then we no-longer mark as read
            if foundMatchedReadChapter:
                if readChapter != chapter['link']:
                    readChapter = None

            readFlag = ''
            # Check if this chapter has been read
            if readAll or (readChapter not in [None, ""]):
                log("EBooksPlugin: Setting chapter as read %s" % chapter['link'])
                readFlag = '* '  # Wanted to use a tick, but it didn't work - u'\u2713'
                # The following will only work it the plug-in is for videos, which in our
                # case it is not (So instead to prepend a character to indicate it has been read
                # li.setInfo('video', {'PlayCount': 1})
            displaytitle = "%s%s" % (readFlag, chapter['title'])

            # Check if this is the last chapter read, as we do not want to flag any more
            # as read if this is as far as we got
            if readChapter == chapter['link']:
                foundMatchedReadChapter = True

            li = xbmcgui.ListItem(displaytitle, iconImage=defaultImage)
            li.setProperty("Fanart_Image", EBookBase.getFanArt(fullpath))
            # Set the Author and book title as the Plot, that will be shown on some skins
            li.setInfo('video', {'Plot': bookAuthorAndTitle})
            li.addContextMenuItems(self._getContextMenu(fullpath, chapter['link'], chapter['previousLink'], chapter['lastChapter']), replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def readChapter(self, fullpath, chapterTitle, chapterLink, isFirstChapter, isLastChapter):
        log("EBooksPlugin: Showing chapter %s" % chapterLink)

        # It could take a little while to get the part of the book required so show the busy dialog
        xbmc.executebuiltin("ActivateWindow(busydialog)")

        # Get the content of the chapter
        eBook = EBookBase.createEBookObject(fullpath)
        chapterContent = eBook.getChapterContents(chapterLink)

        xbmc.executebuiltin("Dialog.Close(busydialog)")

        readerWindow = TextViewer.createTextViewer(chapterTitle, chapterContent, isFirstChapter, isLastChapter)
        # Display the window
        readerWindow.show()

        readStatusChanged = False
        readingChapter = chapterLink
        isShowingLastChapter = isLastChapter
        # Now wait until the text is finished with and the viewer is closed
        while (not readerWindow.isClosed()) and (not xbmc.abortRequested):
            xbmc.sleep(100)

            # Now that the chapter has been read, update the database record
            if readerWindow.isRead():
                readStatusChanged = True
                bookDB = EbooksDB()
                bookDB.setReadChapter(fullpath, readingChapter, isShowingLastChapter)
                del bookDB

            # Check if this chapter is read and a new chapter is to be started
            if readerWindow.isNext():
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                # Find the next chapter
                chapters = self._getChapters(fullpath, eBook)
                nextChapterMatch = False
                for chapter in chapters:
                    # Check if this is the chapter we are moving to
                    if nextChapterMatch:
                        isShowingLastChapter = False
                        if chapter['lastChapter'] == 'true':
                            isShowingLastChapter = True
                        readingChapter = chapter['link']
                        readerWindow.updateScreen(chapter['title'], eBook.getChapterContents(readingChapter), False, isShowingLastChapter)
                        break
                    if chapter['link'] == readingChapter:
                        nextChapterMatch = True
                xbmc.executebuiltin("Dialog.Close(busydialog)")

            if readerWindow.isPrevious():
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                # Find the previous chapter
                chapters = self._getChapters(fullpath, eBook)
                previousChapter = None
                isFirstChapterVal = 'true'
                for chapter in chapters:
                    if chapter['link'] == readingChapter:
                        break
                    previousChapter = chapter['link']
                    isFirstChapterVal = chapter['firstChapter']
                # Check if this is the chapter we are moving to
                if previousChapter not in [None, "", readingChapter]:
                    isShowingLastChapter = False
                    isFirstChapter = False
                    if isFirstChapterVal == 'true':
                        isFirstChapter = True
                    readingChapter = previousChapter
                    readerWindow.updateScreen(chapter['title'], eBook.getChapterContents(readingChapter), isFirstChapter, False)
                xbmc.executebuiltin("Dialog.Close(busydialog)")

        eBook.tidyUp()
        del eBook

        # If this chapter was marked as read then we need to refresh to pick up the record
        if readStatusChanged:
            xbmc.executebuiltin("Container.Refresh")

        del readerWindow

    def _getChapters(self, fullpath, eBook):
        log("EBooksPlugin: Getting chapters for %s" % fullpath)
        # Get the chapters for this book
        chapters = eBook.getChapterDetails()

        chapterList = []

        previousChapterLink = ""
        # Get all the chapters that will be added to the display
        for chapter in chapters:
            # Checks if this is the last chapter of the book
            isLastChapter = 'false'
            if chapter == chapters[-1]:
                log("EBooksPlugin: Last chapter is %s" % chapter['link'])
                isLastChapter = 'true'
            isFirstChapter = 'false'
            if chapter == chapters[0]:
                log("EBooksPlugin: First chapter is %s" % chapter['link'])
                isFirstChapter = 'true'

            chapterItem = {'filename': fullpath, 'title': chapter['title'], 'link': chapter['link'], 'previousLink': previousChapterLink, 'firstChapter': isFirstChapter, 'lastChapter': isLastChapter}

            chapterList.append(chapterItem)
            # Set the previous link so it is available when we do the next loop iteration
            previousChapterLink = chapter['link']

        return chapterList

    # Construct the context menu
    def _getContextMenu(self, filepath, chapterLink="", previousChapterLink="", isLastChapter='false'):
        ctxtMenu = []

        # Check if this is the last chapter of a book, or if it is the book being marked
        # rather than just the chapter
        readFlag = isLastChapter
        if chapterLink in [None, ""]:
            readFlag = 'true'

        # Mark as Read
        cmd = self._build_url({'mode': 'markReadStatus', 'filename': filepath, 'link': chapterLink, 'read': readFlag})
        ctxtMenu.append((ADDON.getLocalizedString(32011), 'RunPlugin(%s)' % cmd))

        # Mark as Not Read
        # Note, marking a chapter as "Not Read" will result in the previous chapter being
        # marked as the last chapter that was read
        cmd = self._build_url({'mode': 'markReadStatus', 'filename': filepath, 'link': previousChapterLink, 'read': 'false'})
        ctxtMenu.append((ADDON.getLocalizedString(32012), 'RunPlugin(%s)' % cmd))

        return ctxtMenu

    def _getBookContextMenu(self, filepath, bookid):
        ctxtMenu = []

        '''shelves = ["Barnabas", "Vera"]'''
        if len(self.shelves) == 0:
            opds = Opds()
            self.shelves = opds.getShelves()

        for shelf in self.shelves:
            cmd = self._build_url({'mode': 'addToShelf', 'bookid': bookid, 'shelf': shelf['id']})
            ctxtMenu.append((ADDON.getLocalizedString(32035) + shelf['title'], 'RunPlugin(%s)' % cmd))
        return ctxtMenu

    def markReadStatus(self, fullpath, chapterLink, markRead):
        # If there is no chapter link then we are clearing the read flag for the whole book
        # If the request was just for a chapter, then we would have been given the previous
        # chapter that would have been marked as read
        bookDB = EbooksDB()
        bookDB.setReadChapter(fullpath, chapterLink, markRead)
        del bookDB

        xbmc.executebuiltin("Container.Refresh")


################################
# Main of the eBooks Plugin
################################
if __name__ == '__main__':
    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Record what the plugin deals with, files in our case - otapi: description doesn't visible at files content on most skins, so set it as movies...
    xbmcplugin.setContent(addon_handle, 'movies')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("EBooksPlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("EBooksPlugin: Mode is NONE - showing root menu")

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.rootMenu()
        del menuNav

    elif mode[0] == 'directory':
        log("EBooksPlugin: Mode is Directory")

        directory = args.get('directory', None)

        if (directory is not None) and (len(directory) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.showEbooksDirectory(directory[0])
            del menuNav

    elif mode[0] == 'chapters':
        log("EBooksPlugin: Mode is CHAPTERS")

        # Get the actual folder that was navigated to
        filename = args.get('filename', None)
        cover = args.get('cover', None)

        if (cover is not None) and (len(cover) > 0):
            cover = cover[0]
        else:
            cover = None

        if (filename is not None) and (len(filename) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.listChapters(filename[0], cover)
            del menuNav

    elif mode[0] == 'readChapter':
        log("EBooksPlugin: Mode is READ CHAPTER")

        # Get the actual chapter that was navigated to
        filename = args.get('filename', None)
        link = args.get('link', None)
        title = args.get('title', None)
        isFirstChapterVal = args.get('firstChapter', None)
        isLastChapterVal = args.get('lastChapter', None)

        if (title is not None) and (len(title) > 0):
            title = title[0]
        else:
            title = ""

        isFirstChapter = False
        if (isFirstChapterVal is not None) and (len(isFirstChapterVal) > 0):
            if isFirstChapterVal[0] == 'true':
                isFirstChapter = True
        isLastChapter = False
        if (isLastChapterVal is not None) and (len(isLastChapterVal) > 0):
            if isLastChapterVal[0] == 'true':
                isLastChapter = True

        if (filename is not None) and (len(filename) > 0) and (link is not None) and (len(link) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.readChapter(filename[0], title, link[0], isFirstChapter, isLastChapter)
            del menuNav

    elif mode[0] == 'markReadStatus':
        log("EBooksPlugin: Mode is MARK READ STATUS")

        filename = args.get('filename', None)
        link = args.get('link', None)
        readStatus = args.get('read', None)

        if (link is not None) and (len(link) > 0):
            link = link[0]
        else:
            link = ""

        markRead = False
        if (readStatus is not None) and (len(readStatus) > 0):
            if readStatus[0] == 'true':
                markRead = True

        if (filename is not None) and (len(filename) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.markReadStatus(filename[0], link, markRead)
            del menuNav

    elif mode[0] == 'opds':
        log("EBooksPlugin: Mode is OPDS")

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.opdsRootMenu()
        del menuNav

    elif mode[0] == 'opds2':
        log("EBooksPlugin: Mode is OPDS 2")

        href = args.get('href', None)

        if (href is not None) and (len(href) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.opdsBookListing(href[0])
            del menuNav

    elif mode[0] == 'addToShelf':
        log("EBooksPlugin: Mode is Add to Shelf")

        shelf = args.get('shelf', None)
        bookid = args.get('bookid', None)

        if (shelf is not None) and (len(href) > 0):
            '''/shelf/add/2/2735'''
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.opdsBookListing(href[0])
            del menuNav
