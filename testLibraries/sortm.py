qualities = ['144p - 1.57MB', '240p - 2.53MB', '360p - 10.79MB', '360p - 4.48MB', '480p - 6.56MB', '720p - 17.72MB', '720p - 11.41MB', '1080p - 39.42MB']


# Extracting resolution and file size from each string and sorting accordingly
def extract_resolution_and_size(quality):
    resolution, size = quality.split(' - ')
    size = float(size.replace('MB', ''))
    resolution = int(resolution.replace('p', ''))
    return resolution, size

# Sorting based on resolution first, then size
qualities_sorted_correctly = sorted(qualities, key=extract_resolution_and_size, reverse=True)

print(qualities, qualities_sorted_correctly)



# https://www.youtube.com/watch?v=KFVdHDMcepw&list=PLJicmE8fK0EiFngx7wBddZDzxogj-shyW&index=3&t=262s