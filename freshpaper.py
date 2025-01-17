import os
import re
import sys
import json
import logging
from random import choice
from datetime import datetime
from subprocess import check_call, CalledProcessError
from PIL import Image

try:
    # for python3
    from urllib.request import urlopen, urlretrieve, HTTPError, URLError
except ImportError:
    # for python2
    from urllib import urlretrieve
    from urllib2 import urlopen, HTTPError, URLError

if sys.platform.startswith("win32"):
    import win32api
    import win32con
    import win32gui

logging.basicConfig(level=logging.INFO, format="%(message)s")

log = logging.getLogger(__name__)


def set_wallpaper(image_path):
    """ Given a path to an image, set it as the wallpaper """
    if not os.path.exists(image_path):
        log.error("Image does not exist.")
        sys.exit(1)

    log.info("Updating wallpaper..")
    log.info(
        "Name of wallpaper: {}".format(
            re.sub("([a-z])([A-Z])", r"\1 \2", image_path.split("/")[-1].split("_")[0])
        )
    )

    if sys.platform.startswith("win32"):

        bmp_image = Image.open(image_path)
        bmp_img_path = os.path.splitext(image_path)[0] + ".bmp"
        bmp_image.save(bmp_img_path, "BMP")
        key = win32api.RegOpenKeyEx(
            win32con.HKEY_CURRENT_USER,
            "Control Panel\\Desktop",
            0,
            win32con.KEY_SET_VALUE,
        )
        win32api.RegSetValueEx(key, "WallpaperStyle", 0, win32con.REG_SZ, "0")
        win32api.RegSetValueEx(key, "TileWallpaper", 0, win32con.REG_SZ, "0")
        win32gui.SystemParametersInfo(
            win32con.SPI_SETDESKWALLPAPER, bmp_img_path, 1 + 2
        )
        os.remove(bmp_img_path)
    elif sys.platform.startswith("darwin"):
        try:
            command = """
                osascript -e 'tell application "System Events"
                    set desktopCount to count of desktops
                    repeat with desktopNumber from 1 to desktopCount
                        tell desktop desktopNumber
                            set picture to "{image_path}"
                        end tell
                    end repeat
                end tell'
                """.format(
                image_path=image_path
            )

            check_call([command], shell=True)
        except CalledProcessError or FileNotFoundError:
            log.error("Setting wallpaper failed.")
            sys.exit(1)
    elif sys.platform.startswith("linux"):
        check_call(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri",
                "file://{}".format(image_path),
            ]
        )

    log.info("Wallpaper successfully updated. :)")


def get_saved_wallpaper(wall_dir):
    """ returns random saved wallpaper's path """

    files = os.listdir(wall_dir)
    if files:
        log.info("\nRandomly picking from saved wallpapers.")
        image_name = choice(files)
        image_path = os.path.join(os.sep, wall_dir, image_name)
        return image_path
    else:
        log.error("There is no wallpaper available offline.")
        sys.exit(1)


def get_wallpaper_directory():
    """ check if `default` wallpaper download directory exists or not, create if doesn't exist """
    pictures_dir = ""
    wall_dir_name = "freshpaper"
    os.path.join(os.sep, os.path.expanduser("~"), "a", "freshpaper")
    if sys.platform.startswith("win32"):
        pictures_dir = "My Pictures"
    elif sys.platform.startswith("darwin"):
        pictures_dir = "Pictures"
    elif sys.platform.startswith("linux"):
        pictures_dir = "Pictures"
    wall_dir = os.path.join(
        os.sep, os.path.expanduser("~"), pictures_dir, wall_dir_name
    )

    if not os.path.isdir(wall_dir):
        log.error("wallpaper directory does not exist.")
        os.makedirs(wall_dir)
        log.info("created wallpaper directory at: {}".format(wall_dir))

    return wall_dir


def download_image(download_dir, image_extension="jpg"):
    """
    Download & save the image
    :param download_dir: directory where to download the image
    :param image_extension: directory where to download the image
    :return: downloaded image path
    """
    # mkt(s) HIN, EN-IN

    url = select_source()
    try:
        image_data = json.loads(urlopen(url).read().decode("utf-8"))

        image_url = "http://www.bing.com" + image_data["images"][0]["url"]

        image_name = re.search(r"OHR\.(.*?)_", image_url).group(1)

        image_url_hd = "http://www.bing.com/hpwp/" + image_data["images"][0]["hsh"]
        date_time = datetime.now().strftime("%d_%m_%Y")
        image_file_name = "{image_name}_{date_stamp}.{extention}".format(
            image_name=image_name, date_stamp=date_time, extention=image_extension
        )

        image_path = os.path.join(os.sep, download_dir, image_file_name)
        log.debug("download_dir: {}".format(download_dir))
        log.debug("image_file_name: {}".format(image_file_name))
        log.debug("image_path: {}".format(image_path))

        if os.path.isfile(image_path):
            log.info("No new wallpaper yet..updating to latest one.\n")
            return image_path

        try:
            log.info("Downloading..")
            urlretrieve(image_url_hd, filename=image_path)
        except HTTPError:
            log.info("Downloading...")
            urlretrieve(image_url, filename=image_path)
        return image_path
    except URLError:
        log.error("Something went wrong.\nThere may be internet issues, or the source is invalid.")
        raise ConnectionError
        
def get_source_list():
    try:
        sources_list = open("sources.txt","r")
        log.info("sources file found!\n")
    except FileNotFoundError:
        log.info("No sources file found, creating it.")
        try: 
            sources_list = open("sources.txt","w")
            sources_list.write("# Enter a URL on each line to add a source to the selector. Lines starting with # are comments.\nhttp://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=EN-IN\n")
        except:
            log.error("The sources file couldn't be created. You may lack the permission to create it. Using Bing as a fallback.")
            return "http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=EN-IN"
    except:
        log.error("Something went wrong while opening the sources file. Using Bing as a fallback.")
        return "http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=EN-IN" 
    sources_available = []
    for line in sources_list: #FIXME: This fails with IndexError unless sources.txt has a bunch of newlines
        is_comment = False
        x = sources_list.readline()
        if (x[0]=='#'):
            is_comment = True
        else:
            sources_available.insert(0,x)
    if (sources_available == []):
        log.info("sources file is empty! Adding default source...")
        sources_list.close()
        sources_list = open("sources.txt", "w")
        sources_list.write("# Enter a URL on each line to add a source to the selector. Lines starting with # are comments.\n")
        sources_list.write("http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=EN-IN\n")
        sources_list.close()
        return "http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=EN-IN"
    return sources_available

def select_source():
    sources_available = get_source_list()
    if (sources_available == "http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=EN-IN"):
        return sources_available
    else:
        x = 0
        for x in range(len(sources_available)):
            log.info(str(x) + ": " + sources_available[x])
        while (True == True):
            try:
                selected_source = sources_available[int(input("Enter source selection: "))]
                return selected_source
            except:
                log.error("Input error.")

def main():
    dir_name = get_wallpaper_directory()  # Wallpaper directory name

    try:
        image_path = download_image(dir_name)
        set_wallpaper(image_path)
    except ConnectionError:
        image_path = get_saved_wallpaper(dir_name)
        set_wallpaper(image_path)
    except Exception as e:
        log.error(e)


if __name__ == "__main__":
    main()
