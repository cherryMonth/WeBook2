# coding=utf-8

import os
import io

import pickle
from surprise import KNNBaseline, Reader
from surprise import Dataset

file_path = os.path.expanduser('.')
# 指定文件格式
reader = Reader(line_format='user item rating timestamp', sep=',')
file_path = os.path.expanduser('favorites.csv')
# 从文件读取数据
music_data = Dataset.load_from_file(file_path, reader=reader)
# 计算歌曲和歌曲之间的相似度
print("构建数据集...")
trainset = music_data.build_full_trainset()

print("开始训练模型...")
algo = KNNBaseline()
algo.train(trainset)
pickle.dump(algo, open('model.pkl', 'wb'))  # 模型导出

user = "1"

# 取出来对应的内部user id => to_inner_uid
playlist_inner_id = algo.trainset.to_inner_uid(user)
print("内部id", playlist_inner_id)

playlist_neighbors = algo.get_neighbors(playlist_inner_id, k=10)

# 把歌曲id转成歌曲名字
# to_raw_uid映射回去
playlist_neighbors = (algo.trainset.to_raw_uid(inner_id)
                       for inner_id in playlist_neighbors)

print("和歌单 《", playlist_neighbors, "》 最接近的10个用户为：\n")
for playlist in playlist_neighbors:
    play_name = playlist.split('\t')
    print play_name
