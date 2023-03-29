from genericpath import exists
import re
import os
from os import listdir
from os.path import isfile, join
import time #for trying to not make google amgery
from random import random #for trying to not make google amgery
import sys # for passing arguments from the console
# -------externals------
from bs4 import BeautifulSoup # for scrapping
import requests # for scrapping
import yt_dlp #for downloading mp3 files from youtube
import mutagen #for tagging downloaded mp3
from mutagen.easyid3 import EasyID3 #for tagging downloaded mp3.
from fuzzywuzzy import fuzz # for fuzzy matching string

# --------------------------------------------


def fuzzy_match_strings(a, b):
    a = str(a).lower()
    b = str(a).lower()
    ratio = fuzz.partial_ratio(a, b)

    # print (f"{a} vs {b}")
    # print (f"ratio: {ratio}")
    return ratio > 0.85

def download_from_youtube(url, filename):
    global PATH_DOWNLOADS
    #TRY: there are youtube links prvided by lastfm that fail. Are unavailable
    #example https://www.youtube.com/watch?v=_yB8Ci7X5HU
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist':True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'{PATH_DOWNLOADS}{filename}.%(ext)s',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(url)

        return True
    except:
        print(f"FAIL: YOUTUBE VIDEO UNAVAILABLE: {url}")
        return False

def google_search(site, artist_name, song_name):

    promising_link = None
    captcha_triggered = False

    # # when making the request, it should say if we are on dektop or mobile.
    # # otherwise the request don't comes formated as expected 
    DESKTOP_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0"
    # MOBILE_USER_AGENT = "Mozilla/5.0 (Linux; Android 7.0; SM-G930V Build/NRD90M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Mobile Safari/537.36"
    headers = {"user-agent" : DESKTOP_USER_AGENT}
    url = f'https://google.com/search?q=site%3A{site}+"{artist_name}"+"{song_name}"'
    page = requests.get(url,headers=headers)
    # # parse request
    soup = BeautifulSoup(page.content, "html.parser")
    # # download_was_successful = download_from_youtube(t_url)

    if (len(soup.findAll('form', id='captcha-form')) > 0):
        # damn, google aready trow us the captcha
        print("!!!! WARNING: GOOGLE IS POLICING WITH THE CAPTCHA :( !!!!")
        captcha_triggered = True
    else:
        google_links = soup.findAll('div', class_='r')
        
        for div in google_links:

            link_title = div.find("h3").string

            if fuzzy_match_strings(artist_name, link_title) and fuzzy_match_strings(song_name, link_title):
                tempty_link = div.find("a")["href"]

                if site == "youtube.com" and any(x in tempty_link for x in ["playlist", "channel", "list"]):
                    # skip urls that have a hardcoded playlist (this are ALWAYS downloaded by youtube-dl)
                    # skip channel links
                    # skip url with "list". TODO: Actually this should be permited. And then check if the track is on there.
                    continue
                elif site == "bandcamp.com" and any(x in tempty_link for x in ["/album/"]):
                    # skip urls of albums. TODO: Actually this should be permited. And then check if the track is on there.
                    continue
                else:
                    promising_link = tempty_link
                    print(promising_link)
                    break

        if promising_link == None:
            print(f"None google link really matched the search of Artist:{artist_name} and Song:{song_name}")

    # or else the google captcha will comes to haunt you at night
    if not captcha_triggered:
        time_to_wait = SECONDS_TO_WAIT_BETWEEN_GOOGLE_SEARCHES + (SECONDS_TO_WAIT_BETWEEN_GOOGLE_SEARCHES*0.1)*random()
        print(f"Sleeping for {round(time_to_wait, 2)} seconds...")
        time.sleep(time_to_wait)

    return promising_link, captcha_triggered            

def download_songs_in_list(user_list):
    global SECONDS_TO_WAIT_BETWEEN_GOOGLE_SEARCHES

    captcha_is_already_triggered = False
    captcha_was_alerted = False
    list_of_tracks_to_download = []
    failed_tracks = []

    unfondsfile_name = "UNFOUNDS.txt"
    if isinstance(user_list, str):
        unfondsfile_name = f"{user_list[0:-4]}_UNFOUNDS.txt"
        #so it's expected a filename to a txt file
        with open(user_list, "r", encoding="utf-8") as f:
            temp_tracks = f.read().split("\n")
            for t in temp_tracks:
                if "||" in t and t not in ["", None]:
                    list_of_tracks_to_download.append(t.split(" || "))
    else:
        list_of_tracks_to_download = user_list

    print(f"There are {len(list_of_tracks_to_download)} songs!")
    print(f"This could take more than {(len(list_of_tracks_to_download)*SECONDS_TO_WAIT_BETWEEN_GOOGLE_SEARCHES)/60} minutes...")
    SECONDS_TO_WAIT_BETWEEN_GOOGLE_SEARCHES

    last_processed_song_index = 0
    files_to_not_dl_again = [f for f in listdir(PATH_DOWNLOADS) if isfile(join(PATH_DOWNLOADS, f))]

    try: # so if conextions is lost or something, we can save all the non downloaded tracks to a file
        #start downloading
        for i, track_data in enumerate(list_of_tracks_to_download):
            
            print(f" ============================= processing {i+1}/{len(list_of_tracks_to_download)}")
            print(f"track_data: {track_data}")
            download_was_successful = False
            t_artist = track_data[0]
            t_title = track_data[1]
            t_url = track_data[2] if len(track_data) >= 3 else None
            t_url = None if t_url == "None" else t_url

            # remove weird characters froms names to be used as the filename
            clean_artist = re.sub(r'[\\~#%&*{}/:<>?|\"-]+', "'", t_artist)
            clean_title = re.sub(r'[\\~#%&*{}/:<>?|\"-]+', "'", t_title)
            filename = f"{clean_artist} - {clean_title}"
            filefullpath = f"{PATH_DOWNLOADS}{filename}.mp3"
            m4afilefullpath = f"{PATH_DOWNLOADS}{filename}.m4a"

            skip = False
            for file in files_to_not_dl_again:
                if file.__contains__(filename):
                    print(f"{filename} is already downloaded. Skipping.")
                    skip = True
                    download_was_successful = True
                    continue

            if not download_was_successful and t_url != None: # Then lastfm already provided a handy youtube link!
                print(f"Trying YOUTUBE provided by LastFM for {filename}")
                download_was_successful = download_from_youtube(t_url, filename)


            # if still no luck, lets try in BANDCAMP!
            if not download_was_successful and not captcha_is_already_triggered:
                print(f"Searching on BANDCAMP for {filename}")
                
                link_to_release, captcha_is_already_triggered = google_search("bandcamp.com", t_artist, t_title)

                if link_to_release != None:
                    print(f"Going to {link_to_release}")
                    # ok, names somewhat matches, so we are good
                    page = requests.get(link_to_release)
                    soup = BeautifulSoup(page.content, 'html.parser')
                    # grab data for tracks (mp3 file and title are in javascript)
                    scripts = soup.findAll('script', type="text/javascript")
                    for script in scripts:    
                        script_as_string = str(script.string) # lol, doble cast. better safe than sorry

                        track_info = re.findall(r"trackinfo:(.*?)\],", script_as_string)
                        if len(track_info) > 0: #skip all the 

                            track_file = re.findall(r"\"file\":(.*?),", track_info[0])
                            if len(track_file) > 0:  # check for fake sites, or no downloads available
                                track_file = track_file[0] # this page should be a "track" type one. so grabbing the first one is fine 
                                if track_file == "null":
                                    print("FAIL!: free reproduction of the song is disabled!")
                                else:
                                    # {"mp3-128":"https://t4.bcbits.com/stream/2ca2dd116679f13a60b3b1a7060f388b/mp3-128/2809292185?p=0&ts=1598108756&t=b80c4e8b8138b337a682c6681b9ec24e1b8a7f1e&token=1598108756_c563b569a2834cced9b91b6226e9dce11e1de430"}
                                    track_file = track_file.split(":", 1)[1]
                                    track_file = track_file[1:-2]
                                    
                                    print(f"DOWNLOADING {t_title} -by- {t_artist} // {link_to_release}")
                                    doc = requests.get(track_file)
                                    with open(filefullpath, 'wb') as f:
                                        f.write(doc.content)

                                    download_was_successful = True
                                    # already found the script with the data, so break out of the loop
                                break

            # if still no luck, lets try searching in YOUTUBE!
            if not download_was_successful and not captcha_is_already_triggered:
                print(f"Searching on YOUTUBE for {filename}")
                link_to_release, captcha_is_already_triggered = google_search("youtube.com", t_artist, t_title)

                if link_to_release != None:
                    download_was_successful = download_from_youtube(link_to_release, filename)

            # TAG
            if download_was_successful :
                #add metatags to the downloaded mp3
                try:
                    if not exists(filefullpath) and exists(m4afilefullpath):
                        filefullpath = m4afilefullpath
                    metatag = EasyID3(filefullpath)
                except mutagen.id3.ID3NoHeaderError:
                    metatag = mutagen.File(filefullpath, easy=True)
                    if len(metatag) == 0: 
                        metatag.add_tags()
                except:
                    print(f"Unknow error while writing metadata on {filename}")
                metatag['title'] = t_title
                metatag['artist'] = t_artist
                metatag.save()
            else:
                if not captcha_was_alerted and captcha_is_already_triggered:
                    failed_tracks.append(f"!!! WARNING: CAPTCHA WAS PROBABLY TRIGGERED FROM HERE :( !!!")
                    captcha_was_alerted = True

                print(f"FAIL FINDING OR DOWNLOADING: {t_title} | {t_artist}")
                failed_tracks.append(f"{t_artist} || {t_title}")

            last_processed_song_index = i+1

    except Exception as e:
        print(e)
    finally:
        # save undownloaded tracks to a file
        non_downloaded_tracks = []
        for t in list_of_tracks_to_download[last_processed_song_index:]:
            non_downloaded_tracks.append(" || ".join(t))
        non_downloaded_tracks = failed_tracks + non_downloaded_tracks

        with open(unfondsfile_name, "w", encoding="utf-8") as logfile:
            logfile.write("\n".join(non_downloaded_tracks))

# GLOBAL CONSTANTS
SECONDS_TO_WAIT_BETWEEN_GOOGLE_SEARCHES = 30
# --------------------------------------------
if __name__ == "__main__":
    try:
        file_list_of_tracks = sys.argv[1]
    except:
        file_list_of_tracks = "mermaidfood-lovedtracks.txt"

    if not os.path.exists("./ffmpeg.exe"):
        print("WARNING: ffmpeg.exe not detected, it is strongly recommanded to use it to download the good formats of songs. You can download it here https://www.ffmpeg.org/download.html ")

    if isinstance(file_list_of_tracks, str):
        #create a folder with the same name of the listfile
        PATH_DOWNLOADS = file_list_of_tracks[0:-4] + "/"
    else:
        PATH_DOWNLOADS = "downloads/"

    #create download folder
    print(PATH_DOWNLOADS)
    if not os.path.exists(PATH_DOWNLOADS):
        os.mkdir(PATH_DOWNLOADS)

    download_songs_in_list(file_list_of_tracks)