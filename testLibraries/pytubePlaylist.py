from pytube import Playlist

p = Playlist("https://www.youtube.com/playlist?list=PLJicmE8fK0EiFngx7wBddZDzxogj-shyW")
print(f'Downloading: {p.title}')
print(f'列表中有{len(p.videos)}个视频')
for video in p.videos:
    # print(video.streams.filter(file_extension='mp4'))
    print(video.streams.get_by_itag(137))
    # video.streams.first().download()