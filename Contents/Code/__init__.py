import os, time, random

####################################################################################################

PREFIX = "/video/unsupportedappstore"

NAME = 'UnSupported AppStore'

ART         = 'art-default.jpg'
ICON        = 'icon-default.png'
PREFS_ICON  = 'icon-prefs.png'

PLUGINS     = 'plugin_details.json'

DEV_MODE    = False

####################################################################################################

def Start():

    HTTP.CacheTime = 0
    
    DirectoryObject.thumb = R(ICON)
    ObjectContainer.art = R(ART)
    
    #Check the list of installed plugins
    if Dict['Installed'] == None:
        Dict['Installed'] = {'UnSupported Appstore' : {'lastUpdate': 'None', 'updateAvailable': 'False', 'installed': 'True'}}
    else:
        if not Dict['Installed']['UnSupported Appstore']['installed']:
            Dict['Installed']['UnSupported Appstore']['installed'] = True
        Logger(Dict['Installed'])
        
    Logger('Plex support files are at ' + Core.app_support_path)
    Logger('Plug-in bundles are located in ' + Core.storage.join_path(Core.app_support_path, Core.config.bundles_dir_name))
    Logger('Plug-in support files are located in ' + Core.storage.join_path(Core.app_support_path, Core.config.plugin_support_dir_name))
    
    if Prefs['auto-update']:
        Thread.Create(BackgroundUpdater)
 
@handler(PREFIX, NAME, "icon-default.png", "art-default.jpg")
def MainMenu():
    
    #Load the list of available plugins
    Dict['plugins'] = LoadData()
    
    oc = ObjectContainer(no_cache=True)
    
    oc.add(DirectoryObject(key=Callback(CheckForUpdates, return_message=True), title="Check for updates"))
    oc.add(DirectoryObject(key=Callback(GenreMenu, genre='New'), title='New'))
    oc.add(DirectoryObject(key=Callback(GenreMenu, genre='All'), title='All'))
    if Prefs['adult']:
        oc.add(DirectoryObject(key=Callback(GenreMenu, genre='Adult'), title='Adult'))
    oc.add(DirectoryObject(key=Callback(GenreMenu, genre='Application'), title='Application'))
    oc.add(DirectoryObject(key=Callback(GenreMenu, genre='Video'), title='Video'))
    oc.add(DirectoryObject(key=Callback(GenreMenu, genre='Pictures'), title='Pictures'))
    oc.add(DirectoryObject(key=Callback(GenreMenu, genre='Metadata Agent'), title='Metadata Agent'))
    oc.add(DirectoryObject(key=Callback(GenreMenu, genre='Music'), title='Music'))
    oc.add(DirectoryObject(key=Callback(InstalledMenu), title='Installed'))
    oc.add(DirectoryObject(key=Callback(UpdateAll), title='Download updates',
        summary="Update all installed plugins.\nThis may take a while and will require you to restart PMS for changes to take effect"))
    oc.add(PrefsObject(title="Preferences", thumb=R(PREFS_ICON)))

    return oc

@route(PREFIX + '/genre')
def GenreMenu(genre):
    oc = ObjectContainer(title2=genre, no_cache=True)
    plugins = Dict['plugins']
    if genre == 'New':
        try:
            for plugin in plugins:
                plugin['date added'] = Datetime.TimestampFromDatetime(Datetime.ParseDate(plugin['date added']))
        except:
            Log.Exception("Converting dates to timestamps failed")
        date_sorted = sorted(plugins, key=lambda k: k['date added'])
        Logger(date_sorted)
        date_sorted.reverse()
        plugins = date_sorted
    
    for plugin in plugins:
        if plugin['hidden'] == "True": continue ### Don't display plugins which are "hidden"
        else: pass
        if plugin['title'] != "UnSupported Appstore":
            if not Prefs['adult']:
                if "Adult" in plugin['type']:
                    continue
                else:
                    pass
            else:
                pass
            if genre == 'All' or genre == 'New' or genre in plugin['type']:
                if Installed(plugin):
                    if Dict['Installed'][plugin['title']]['updateAvailable'] == "True":
                        subtitle = 'Update available\n'
                    else:
                        subtitle = 'Installed\n'
                else:
                    subtitle = ''
                oc.add(PopupDirectoryObject(key=Callback(PluginMenu, plugin=plugin), title=plugin['title'],
                    summary=subtitle + plugin['description'], thumb=R(plugin['icon'])))
    if len(oc) < 1:
        return ObjectContainer(header=NAME, message='There are no plugins to display in the list: "%s"' % genre)
    return oc

@route(PREFIX + '/installed')
def InstalledMenu():
    oc = ObjectContainer(title2="Installed", no_cache=True)
    plugins = Dict['plugins']
    plugins.sort()
    for plugin in plugins:
        summary = ''
        if Installed(plugin):
            if plugin['hidden'] == "True":
                summary = 'No longer available through the Unsupported Appstore'
            elif Dict['Installed'][plugin['title']]['updateAvailable'] == "True":
                summary = 'Update available'
            else: pass
            oc.add(PopupDirectoryObject(key=Callback(PluginMenu, plugin=plugin), title=plugin['title'],summary=summary,
                thumb=R(plugin['icon'])))
    return oc

@route(PREFIX + '/popup', plugin=dict)
def PluginMenu(plugin):
    oc = ObjectContainer(title2=plugin['title'], no_cache=True)
    if Installed(plugin):
        if Dict['Installed'][plugin['title']]['updateAvailable'] == "True":
            oc.add(DirectoryObject(key=Callback(InstallPlugin, plugin=plugin), title="Update"))
        oc.add(DirectoryObject(key=Callback(UnInstallPlugin, plugin=plugin), title="UnInstall"))
    else:
        oc.add(DirectoryObject(key=Callback(InstallPlugin, plugin=plugin), title="Install"))
    return oc
  
@route(PREFIX + '/load')
def LoadData():
    userdata = Resource.Load(PLUGINS)
    return JSON.ObjectFromString(userdata)

@route(PREFIX + '/installedcheck', plugin=dict)
def Installed(plugin):
    try:
        if Dict['Installed'][plugin['title']]['installed'] == "True":
            return True
        else:
            return False
    except:
        ### make sure the Appstore shows up in the list if it doesn't already ###
        if plugin['title'] == 'UnSupported Appstore':
            Dict['Installed'][plugin['title']] = {"installed":"True", "lastUpdate":"None", "updateAvailable":"False"}
            Dict.Save()
        else:
            Dict['Installed'][plugin['title']] = {"installed":"False", "lastUpdate":"None", "updateAvailable":"True"}
            Dict.Save()
        return False
    
    return False

@route(PREFIX + '/installplugin', plugin=dict)
def InstallPlugin(plugin):
    if Installed(plugin):
        Install(plugin)
    else:
        Install(plugin, initial_download=True)
    return ObjectContainer(header=NAME, message='%s installed, restart PMS for changes to take effect.' % plugin['title'])

def JoinBundlePath(plugin, path):
    bundle_path = GetBundlePath(plugin)
    fragments = path.split('/')[1:]

    # Remove the first fragment if it matches the bundle name
    if len(fragments) and fragments[0].lower() == plugin['bundle'].lower():
        fragments = fragments[1:]

    return Core.storage.join_path(bundle_path, *fragments)

@route(PREFIX + '/install', plugin=dict, initial_download=bool)
def Install(plugin, initial_download=False):
    if initial_download:
        zipPath = plugin['tracking url']
    else:
        zipPath = 'http://%s/archive/%s.zip' % (plugin['repo'].split('@')[1].replace(':','/')[:-4], plugin['branch'])
    Logger('zipPath = ' + zipPath)
    Logger('Downloading from ' + zipPath)
    zipfile = Archive.ZipFromURL(zipPath)

    bundle_path = GetBundlePath(plugin)
    Logger('Extracting to ' + bundle_path)
    
    for filename in zipfile:
        data = zipfile[filename]

        if not str(filename).endswith('/'):
            if not str(filename.split('/')[-1]).startswith('.'):
                path = JoinBundlePath(plugin, filename)

                Logger('Extracting file' + path)
                Core.storage.save(path, data)
            else:
                Logger('Skipping "hidden" file: ' + filename)
        else:
            Logger(filename.split('/')[-2])

            if not str(filename.split('/')[-2]).startswith('.'):
                path = JoinBundlePath(plugin, filename)

                Logger('Extracting folder ' + path)
                Core.storage.ensure_dirs(path)
    
    MarkUpdated(plugin['title'])
    # "touch" the bundle to update the timestamp
    os.utime(bundle_path, None)
    return

@route(PREFIX + '/updateall')
def UpdateAll():
    for plugin in Dict['plugins']:
        if Dict['Installed'][plugin['title']]['installed'] == "True":
            if Dict['Installed'][plugin['title']]['updateAvailable'] == "False":
                Logger('%s is already up to date.' % plugin['title'])
            else:
                Logger('%s is installed. Downloading updates:' % (plugin['title']))
                update = Install(plugin)
                Logger(update)
        else:
            Logger('%s is not installed.' % plugin['title'])
            pass

    return ObjectContainer(header=NAME, message='Updates have been applied. Restart PMS for changes to take effect.')

@route(PREFIX + '/uninstall', plugin=dict)
def UnInstallPlugin(plugin):
    Logger('Uninstalling %s' % GetBundlePath(plugin))
    try:
        if Prefs['delete_data']:
            try:
                DeleteFolder(GetSupportPath('Caches', plugin))
                DeleteFolder(GetSupportPath('Data', plugin))
                DeleteFolder(GetSupportPath('Preferences', plugin))
            except:
                Logger("Failed to remove support files. Attempting to uninstall plugin anyway.")
        DeleteFolder(GetBundlePath(plugin))
    except:
        Logger("Failed to remove all the bundle's files but we'll mark it uninstalled anyway.")
    Dict['Installed'][plugin['title']]['installed'] = "False"
    Dict.Save()
    return ObjectContainer(header=NAME, message='%s uninstalled. Restart PMS for changes to take effect.' % plugin['title'])

@route(PREFIX + '/deletefile')
def DeleteFile(filePath):
    Logger('Removing ' + filePath)
    os.remove(filePath)
    return

@route(PREFIX + '/deletefolder')
def DeleteFolder(folderPath):
    Logger('Attempting to delete %s' % folderPath)
    if os.path.exists(folderPath):
        for file in os.listdir(folderPath):
            path = Core.storage.join_path(folderPath, file)
            try:
                DeleteFile(path)
            except:
                DeleteFolder(path)
        Logger('Removing ' + folderPath)
        os.rmdir(folderPath)
    else:
        Logger("%s doesn not exist so we don't need to remove it" % folderPath)
    return
    
@route(PREFIX + '/updatecheck')
def CheckForUpdates(install=False, return_message=False):
    #use the github commit feed for each installed plugin to check for available updates
    @parallelize
    def GetUpdateList():
        for num in range(len(Dict['plugins'])):
            @task
            def GetRSSFeed(num=num):
                plugin = Dict['plugins'][num]
                if Installed(plugin):
                    rssURL = 'https://%s/commits/%s.atom' % (plugin['repo'].split('@')[1].replace(':','/')[:-4], plugin['branch'])
                    commits = HTML.ElementFromURL(rssURL)
                    mostRecent = Datetime.ParseDate(commits.xpath('//entry')[0].xpath('./updated')[0].text[:-6])
                    if Dict['Installed'][plugin['title']]['lastUpdate'] == "None":
                        Dict['Installed'][plugin['title']]['updateAvailable'] = "True"
                    elif mostRecent > Dict['Installed'][plugin['title']]['lastUpdate']:
                        Dict['Installed'][plugin['title']]['updateAvailable'] = "True"
                    else:
                        Dict['Installed'][plugin['title']]['updateAvailable'] = "False"
                    
                    if Dict['Installed'][plugin['title']]['updateAvailable'] == "True":
                        Logger(plugin['title'] + ': Update available')
                        if install:
                            if plugin['title'] == 'UnSupported Appstore' and DEV_MODE:
                                pass
                            else:
                                update = Install(plugin)
                                Logger(update)            
                    else:
                        Logger(plugin['title'] + ': Up-to-date')
        Dict.Save()
    if return_message:
        return ObjectContainer(header="Unsupported Appstore", message="Update check complete.")
    else:
        return


@route(PREFIX + '/updater')
def BackgroundUpdater():
    while Prefs['auto-update']:
        Logger("Running auto-update.")
        CheckForUpdates(install=True)
        # check for updates every 24hours... give or take 30 minutes to avoid hammering GitHub
        sleep_time = 24*60*60 + (random.randint(-30,30))*60
        hours, minutes = divmod(sleep_time/60, 60)
        Logger("Updater will run again in %d hours and %d minutes" % (hours, minutes))
        while sleep_time > 0:
            remainder = sleep_time%(3600)
            if  remainder > 0:
                time.sleep(remainder)
                sleep_time = sleep_time - remainder
            Logger("Time until next auto-update = %d hours" % (int(sleep_time)/3600))
            sleep_time = sleep_time - 3600
            time.sleep(3600)
    return
    
@route(PREFIX + '/plugindir')
def GetPluginDirPath():
    return Core.storage.join_path(Core.app_support_path, Core.config.bundles_dir_name)

@route(PREFIX + '/bundlepath', plugin=dict)    
def GetBundlePath(plugin):
    return Core.storage.join_path(GetPluginDirPath(), plugin['bundle'])

@route(PREFIX + '/supportpath', plugin=dict)
def GetSupportPath(directory, plugin):
    if directory == 'Preferences':
        return Core.storage.join_path(Core.app_support_path, Core.config.plugin_support_dir_name, directory, (plugin['identifier'] + '.xml'))
    else:
        return Core.storage.join_path(Core.app_support_path, Core.config.plugin_support_dir_name, directory, plugin['identifier'])

@route(PREFIX + '/logger')
def Logger(message):
    if Prefs['debug']:
        Log(message)
    else:
        pass

'''allow plugins to mark themselves updated externally'''
@route('%s/mark-updated/{title}' % PREFIX)
def MarkUpdated(title):
    Dict['Installed'][title]['installed'] = "True"
    Logger('%s "Installed" set to: %s' % (title, Dict['Installed'][title]['installed']))
    Dict['Installed'][title]['lastUpdate'] = Datetime.Now()
    Logger('%s "LastUpdate" set to: %s' % (title, Dict['Installed'][title]['lastUpdate']))
    Dict['Installed'][title]['updateAvailable'] = "False"
    Logger('%s "updateAvailable" set to: %s' % (title, Dict['Installed'][title]['updateAvailable']))
    Dict.Save()
    