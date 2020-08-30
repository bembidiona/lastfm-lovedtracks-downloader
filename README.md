# lastfm-lovedtracks-downloader
Download all loved tracks from any [Last.fm](https://www.last.fm) user as nicelly tagged mp3 files

### HOW TO USE
1- First pass a valid username to the `lastfm-lovedtracks-to-list.py` script:  
```
python lastfm-lovedtracks-to-list.py username
```

2- Pass this new generated file to the `downloader.py` script:  
```
python downloader.py username-lovedtracks.txt
```

3- Just wait for the downloads to finish!

3½- If your internet disconect or something goes wrong, a file name `username-lovedtracks_UNFOUND.txt` will be created. You can resume downloading as:
```
python downloader.py username-lovedtracks_UNFOUND.txt
```
