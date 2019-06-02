# def produce_user():
#     for i in range(1, 100):
#         import base64
#         import random
#         hbase = HBaseDBConnection()
#         image_num = random.randint(1, 28)
#         file = open("img/" + str(image_num) + ".png", 'rb')
#         user = User(email="111506445{}@qq.com".format(i), username=u"测试用户{}".format(i),
#                     password="123456")
#         db.session.add(user)
#         db.session.commit()
#         image = base64.b64encode(file.read()).decode('utf8')
#         user_id = User.query.filter_by(username=u"测试用户{}".format(i)).first().id
#         hbase.execute_insert('image', 'user_{}'.format(user_id), ['image_type', 'image'], ['png', image])
#         hbase.dbpool.close()
#
#
# def produce_category():
#     import pandas as pd
#     import datetime
#     data = pd.read_csv('hot.csv')
#     user_list = User.query.filter(id>0).all()
#     user_index = [user.id for user in user_list]
#     import random
#     for index, row in data.iterrows():
#         try:
#             p = Category()
#             p.title = row['name']
#             p.content = u"""# 景区级别\r\n\r\n{}\r\n\r\n# 景区价格\r\n\r\n{}\r\n\r\n# 景区简介\r\n\r\n{}\r\n\r\n![]({})""".format(
#                 row['level'], row['price'], row['info'], row['image_url'])
#             p.user = random.sample(user_index, 1)[0]
#             p.location = row['address']
#             p.topic = Topic.query.filter_by(topic_name=row['area'].split('·')[0][1:]).first().id
#             p.update_time = datetime.datetime.utcnow()
#             db.session.add(p)
#             db.session.commit()
#         except Exception as e:
#             print(e)

