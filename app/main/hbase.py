# coding=utf-8

import happybase


class HBaseDBConnection(object):
    image_type = 'image_type'
    image = 'image'  # 图片

    def __init__(self):
        self.dbpool = happybase.Connection(host='192.168.0.148', port=9090, protocol='binary')
        self.check_table()

    def check_table(self, table_name='image'):
        try:
            if not self.dbpool.is_table_enabled(table_name):
                print('table %s does not enable, Try to enable it!' % (table_name,))
                self.dbpool.enable_table(table_name)
                print('enable %s table collect success!' % (table_name,))
        except Exception:
            print('table %s does not existed, try to create it!' % (table_name,))
            self.create_table(table_name)
            print('create %s success!' % (table_name,))

    def create_table(self, name):

        familes = {self.image_type: dict(), self.image: dict()}
        self.dbpool.create_table(name, familes)

    def execute_insert(self, family, row, column_names, data_listes, table_name='image'):

        """
        为了封装execute_insert 函数使其调用规则类似SQL
        参数接收所有的列名以及列对应的数据
        无论是hbase还是sql 只需要填充列名和列对应的属性即可
        example:
        family = 'sensor'
        column_names = ['id', 'type', 'entry_time']
        data_listes = ['1', '温度', '2017']
        db.execute_insert(column_names, data_listes, family)
        :param column_names:
        :param data_listes:
        :param table_name:
        :param family:
        :return:
        """

        cmd = dict()

        for index in range(len(column_names)):
            cmd[family + ":" + column_names[index]] = str(data_listes[index])

        self.dbpool.table(table_name).put(str(row), cmd)

    def delete_row(self, table, row):
        self.dbpool.table(table).delete(row)

    def query_by_row(self, table, row):
        return self.dbpool.table(table).row(row=row)


hbase = HBaseDBConnection()

if __name__ == '__main__':
    # db.execute_insert('test', ['id', 'name', 'password'], ['123', 123, 123])
    import base64

    db = HBaseDBConnection()
    # print(db.dbpool.table('image'))
    # file = open('3.png', 'rb')
    # db.delete_row('image', 'adas')
    # db.execute_insert('image', 'adas', ['image_type', 'image'], ['123', image])
    file_bytes = db.query_by_row('image', 'a.jpg')
    print(file_bytes)
    # print(file_bytes.keys())
    # file = open('test.jpg', 'wb')
    # result = base64.b64decode(file_bytes.decode())
    # file.write(result)
    # file.close()