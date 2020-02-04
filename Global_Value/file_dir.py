# encoding=utf-8
import os

config_path = 'c:/MoDeng/'
data_source_url = config_path+'data_source.json'
stk_config_url = config_path+'stk_config.json'
data_dir = config_path + 'data/'

json_file_url = data_dir + '\last_p.json'
opt_record_file_url = data_dir + '\opt_record.json'

hist_pic_dir = data_dir+'temp_pic/'                         # 小时更新图片存放路径
sea_select_pic_dir = data_dir + 'Sea_Select_Pic_tmp/'       # 海选图片存放路径


# 全局变量，记录操作细节
opt_record = []

# 源代码根目录
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = curPath[:curPath.find("MoDeng\\")+len("MoDeng\\")]  # 获取myProject，也就是项目的根路径

