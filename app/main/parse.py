import re


class Extractor(object):

    def __init__(self, blockSize=3):
        self.blockSize = blockSize

        # Compile re
        self.reDATA = re.compile('<!DOCTYPE.*?>', re.I | re.S)
        # HTML comment
        self.reComment = re.compile('<!--[\s\S]*?-->')
        # Scripts
        self.reScript = re.compile('<\s*script[^>]*>[\w\W]*?<\s*/\s*script\s*>', re.I)
        # CSS
        self.reStyle = re.compile('<\s*style[^>]*>[^<]*<\s*/\s*style\s*>', re.I)
        # HTML Tag
        self.reTag = re.compile('<[\s\S]*?>')
        # Special charcaters
        self.reSpecial = re.compile('&.{1,5};|&#.{1,5};')
        # Spaces
        self.reSpace = re.compile('\s+')
        # Word wrap transform
        self.reWrap = re.compile('\r\n|\r')
        # Reduce redundancy
        self.reRedun = re.compile('\n{%s,}' % (self.blockSize + 1))

    def reset(self):
        self.text = ''
        self.isGB = True
        self.textLines = []
        self.blocksLen = []
        self.isCharsetGB = True

    def handleEncoding(self):
        match = re.search('charset\s*=\s*"?([\w\d-]*)"?', self.rawPage, re.I)
        if match:
            charset = match.group(1).lower()
            if charset.find('gb') == -1:
                self.isCharsetGB = False
        else:
            self.isCharsetGB = False

    def preProcess(self, doc):
        doc = self.reDATA.sub('', doc)
        doc = self.reComment.sub('', doc)
        doc = self.reScript.sub('', doc)
        doc = self.reStyle.sub('', doc)
        doc = self.reTag.sub('', doc)
        doc = self.reSpecial.sub('', doc)
        doc = self.reWrap.sub('\n', doc)
        doc = self.reRedun.sub('\n' * (self.blockSize + 1), doc)
        return doc

    # Split the preprocessed text into lines by '\n'
    def getTextLines(self, text):
        lines = text.split('\n')
        for line in lines:
            if line:
                line = self.reSpace.sub('', line)
            self.textLines.append(line)
        return ''.join(self.textLines)

    # Calculate the length of every block
    def calcBlockLens(self):
        textLinesCnt = len(self.textLines)
        blockLen = 0
        blockSize = min([textLinesCnt, self.blockSize])
        for i in range(blockSize):
            blockLen = blockLen + len(self.textLines[i])
            self.blocksLen.append(blockLen)

        if (blockSize != self.blockSize):
            return

        for i in range(1, textLinesCnt - self.blockSize):
            blockLen = self.blocksLen[i - 1] \
                       + len(self.textLines[i - 1 + self.blockSize]) \
                       - len(self.textLines[i - 1])
            self.blocksLen.append(blockLen)

    # Merge the most possibile blocks as the final plaintext
    def getPlainText(self, data=''):
        self.reset()
        self.rawPage = data
        self.handleEncoding()
        preProcDoc = self.preProcess(data)
        # f = open('dump')
        # preProcDoc = f.read()
        self.text = self.getTextLines(preProcDoc)

        if self.isCharsetGB:
            try:
                print(self.text)
                self.text = self.text.decode('gb2312').encode('utf-8')
            except Exception:
                print('error')
                pass
        return self.text


if __name__ == '__main__':
    ext = Extractor(3)
    html = """<p><img alt="" src="https://upload-images.jianshu.io/upload_images/6551115-aace0a7317cd6bb8.jpg?imageMogr2/auto-orient/strip%7CimageView2/2/w/1000/format/webp" /></p>
    <p>今天不用早起，孩子们都在睡觉，我和先生八点多起来，简单吃过早餐后他看新闻，我开始整理床头和书柜里的部分书籍，准备把一些书带回榆林去。每收拾一本都会勾起一些回忆，我拿起给先生一一介绍着。有些是在书店甚至是街边的书摊上淘到的，有些是网购，还有些是朋友和大学舍友送的……2013年，大宝考入工大附中读高中，全家全力以赴支持，三月份刚办了退休手续的老爸和老妈负责大宝全部后勤，我和先生榆林西安两边跑。大宝小宝都是我一手带大的，孩子们有些依赖我，自然是我来回跑得多，基本是一半时间在榆林一半时间在西安，高三后半学期开始全程陪读。这些书就是2013年后半学期开始陆陆续续来到我和大宝身边的。大宝因为时间关系，只能读一小部分课外书。《黄帝内经》养生之类的是先生在读，其他的基本都是我的。我属于“杂读”型，除了《本草纲目》这些特别专业的不读之外，无论是大宝的少年版还是典藏版我都读。小宝来了我会给她读读《小王子》和《老人与海》，其他的她不感兴趣。</p>"""
    print(ext.getPlainText(html))
