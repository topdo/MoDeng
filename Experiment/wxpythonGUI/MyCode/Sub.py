# encoding=utf-8

""" =========================== 将当前路径及工程的跟目录添加到路径中，必须在文件头部，否则易出错 ============================ """
import sys
import os

from Experiment.wxpythonGUI.DengShen.Sub import sub

curPath = os.path.abspath(os.path.dirname(__file__))
if "MoDeng" in curPath:
    rootPath = curPath[:curPath.find("MoDeng\\")+len("MoDeng\\")]  # 获取myProject，也就是项目的根路径
elif "MoDeng-master" in curPath:
    rootPath = curPath[:curPath.find("MoDeng-master\\") + len("MoDeng-master\\")]  # 获取myProject，也就是项目的根路径
else:
    print('没有找到项目的根目录！请检查项目根文件夹的名字！')
    exit(1)

sys.path.append('..')
sys.path.append(rootPath)

import copy
import matplotlib
matplotlib.use('agg')
import threading
import time
import win32gui
import wx
import wx.xrc
import wx.grid
import pandas as pd
import numpy as np
import json

from Experiment.wxpythonGUI.MyCode.note_string import note_init_pic, note_day_analysis
from AutoDailyOpt.Sub import JudgeSingleStk, calRSVRank
from Experiment.wxpythonGUI.MyCode.Thread_Sub import ResultEvent
from Config.AutoGenerateConfigFile import data_dir, checkConfigFile
from Experiment.MiddlePeriodLevelCheck.Demo1 import check_single_stk_middle_level, update_middle_period_hour_data
from AutoDailyOpt.p_diff_ratio_last import RSV_Record, MACD_min_last
from Config.Sub import dict_stk_list, readConfig
from DataSource.Code2Name import code2name
from Experiment.wxpythonGUI.MyCode.Data_Pro_Sub import get_pic_dict

from SDK.Gen_Stk_Pic_Sub import gen_Hour_MACD_Pic_wx, \
    gen_Day_Pic_wx, gen_W_M_MACD_Pic_wx, gen_Idx_Pic_wx, gen_hour_macd_values
from SDK.MyTimeOPT import get_current_datetime_str

# 定义事件id
INIT_CPT_ID = wx.NewIdRef(count=1)
HOUR_UPDATE_ID = wx.NewIdRef(count=1)

MSG_UPDATE_ID_A = wx.NewIdRef(count=1)
MSG_UPDATE_ID_S = wx.NewIdRef(count=1)

NOTE_UPDATE_ID_A = wx.NewIdRef(count=1)
NOTE_UPDATE_ID_S = wx.NewIdRef(count=1)

LAST_TIME_UPDATE_ID = wx.NewIdRef(count=1)

FLASH_WINDOW_ID = wx.NewIdRef(count=1)


def get_t_now():
    r = get_current_datetime_str()
    h, m, s = r.split(' ')[1].split(':')
    return int(h + m)


# 线程全局参数
last_upt_t = get_t_now()


class MyImageRenderer(wx.grid.GridCellRenderer):
    def __init__(self, img):
        wx.grid.GridCellRenderer.__init__(self)
        self.img = img

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        image = wx.MemoryDC()
        image.SelectObject(self.img)
        dc.SetBackgroundMode(wx.SOLID)
        if isSelected:
            dc.SetBrush(wx.Brush(wx.BLUE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.BLUE, 1, wx.SOLID))
        else:
            dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.WHITE, 1, wx.SOLID))
        dc.DrawRectangle(rect)
        width, height = self.img.GetWidth(), self.img.GetHeight()
        if width > rect.width - 2:
            width = rect.width - 2
        if height > rect.height - 2:
            height = rect.height - 2
        dc.Blit(rect.x + 1, rect.y + 1, width, height, image, 0, 0, wx.COPY, True)


class MyPanelText(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.Size(500, 300),
                          style=wx.TAB_TRAVERSAL)

        bSizer1 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_textCtrlNote = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=wx.Size(550, 800))
        self.m_textCtrlNote.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.m_textCtrlNote.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))

        self.m_textCtrlMsg = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=wx.Size(550, 800))
        self.m_textCtrlMsg.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.m_textCtrlMsg.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))

        bSizer1.Add(self.m_textCtrlNote, 0, wx.ALL, 5)
        bSizer1.Add(self.m_textCtrlMsg, 0, wx.ALL, 5)

        self.SetSizer(bSizer1)
        self.Layout()

    def __del__(self):
        pass


class MyPanelGrid(wx.Panel):

    def __init__(self, parent, stk_info):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.Size(500, 300),
                          style=wx.TAB_TRAVERSAL)

        bSizer4 = wx.BoxSizer(wx.VERTICAL)

        self.my_grid4 = wx.grid.Grid(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)

        # Grid
        self.my_grid4.CreateGrid(len(stk_info), 5)
        self.my_grid4.EnableEditing(True)
        self.my_grid4.EnableGridLines(True)
        self.my_grid4.EnableDragGridSize(False)
        self.my_grid4.SetMargins(0, 0)

        # Columns
        self.my_grid4.EnableDragColMove(False)
        self.my_grid4.EnableDragColSize(True)
        self.my_grid4.SetColLabelSize(30)
        self.my_grid4.SetColLabelAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

        self.my_grid4.SetColLabelValue(0, "定时检测")
        self.my_grid4.SetColLabelValue(1, "小时M")
        self.my_grid4.SetColLabelValue(2, "日M")
        self.my_grid4.SetColLabelValue(3, "周/月M")
        self.my_grid4.SetColLabelValue(4, "其他指数")

        # Rows
        self.my_grid4.EnableDragRowSize(True)
        self.my_grid4.SetRowLabelSize(80)
        self.my_grid4.SetRowLabelAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)
        # self.my_grid4.SetRowLabelValue()

        # Add name to Rows
        self.addRowName([(k, v[0]) for k, v in stk_info.items()])

        # Add pic to cell
        for code, img in stk_info.items():
            self.insert_Pic_To_Cell(img[0], 1, img[1]['hour'])
            self.insert_Pic_To_Cell(img[0], 2, img[1]['day'])
            self.insert_Pic_To_Cell(img[0], 3, img[1]['wm'])
            self.insert_Pic_To_Cell(img[0], 4, img[1]['index'])

        # Label Appearance

        # Cell Defaults
        self.my_grid4.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)

        # 设置行间隔
        # self.my_grid4.SetMargins(0, 2)

        bSizer4.Add(self.my_grid4, 0, wx.ALL, 5)

        self.SetSizer(bSizer4)
        self.Layout()

    def __del__(self):
        pass

    def addRowName(self, stk_code_list):
        """
        添加行名称
        :param stk_code_list:
        :return:
        """

        for info in stk_code_list:
            self.my_grid4.SetRowLabelValue(info[1], code2name(info[0]))

    def insert_Pic_To_Cell(self, r, c, img):
        """

        :param r:
        :param c:
        :param pic:
        :return:
        """

        img_Rd = MyImageRenderer(wx.Bitmap(img))
        self.my_grid4.SetCellRenderer(r, c, img_Rd)
        self.my_grid4.SetColSize(c, img.GetWidth() + 2)
        self.my_grid4.SetRowSize(r, img.GetHeight() + 2)


def timer_update_pic(kind):

    """
    在计时器中调用，用于更新小时图片
    :param kind:
    h:小时
    d:天
    wm:周、月
    idx: 指数
    :return:

    返回的图片应该 执行page和行号，便于更新！
    以多层字典的方式返回结果，第一层区分page，第二层区分行号！
    """
    r_dic = {
        'Index': {},
        'Buy': {},
        'Concerned': {}
    }
    dict_stk_hour = copy.deepcopy(dict_stk_list)
    for page in dict_stk_hour.keys():
        for stk_info in dict_stk_list[page]:
            stk = stk_info[1]
            if kind is 'h':
                r_dic[page][stk] = (stk_info[0], gen_Hour_MACD_Pic_wx(stk))
            elif kind is 'd':
                r_dic[page][stk] = (stk_info[0], gen_Day_Pic_wx(stk))
            elif kind is 'wm':
                r_dic[page][stk] = (stk_info[0], gen_W_M_MACD_Pic_wx(stk))
            elif kind is 'idx':
                r_dic[page][stk] = (stk_info[0], gen_Idx_Pic_wx(stk))

    # 汇总返回
    return r_dic


def check_stk_list_middle_level(stk_list):
    """
    检测一系列stk的中期水平
    :param stk_list:
    :param threshold:
    :return:
    """
    if not os.path.exists(data_dir+'middlePeriodHourData.json'):
        update_middle_period_hour_data()

    # 读取历史小时数据
    with open(data_dir+'middlePeriodHourData.json', 'r') as f:
        dict = json.load(f)

    r = [(x, (1-check_single_stk_middle_level(x, dict)/100)*100) for x in list(set(stk_list))]
    r_df = pd.DataFrame(data=r, columns=['code', 'level_value'])
    r_df['name'] = r_df.apply(lambda x: code2name(x['code']), axis=1)
    r_df_sort = r_df.sort_values(by='level_value', ascending=True).head(12)
    r_df_sort['level'] = r_df_sort.apply(lambda x: '%0.2f' % x['level_value'] + '%', axis=1)

    r_df_sort = r_df_sort.loc[:, ['name', 'level']].reset_index(drop=True)

    return r_df_sort


def OnTimerWorkThread(win, debug=False):

    # 进行图片初始化并打印提示
    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data='正在初始化图片...\n'))
    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data=note_init_pic))

    # 更新图片及打印分析结果
    r = get_pic_dict()
    wx.PostEvent(win, ResultEvent(id=INIT_CPT_ID, data=r[0]))
    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data='图片初始化完成！\n'))

    # 向提示框打印日线判断提示
    wx.PostEvent(win, ResultEvent(
        id=NOTE_UPDATE_ID_A,
        data=ChangeFontColor(note_day_analysis)))

    if len(r[1]) > 0:

        # 向提示框打印提示
        for note_str in r[1]:
            wx.PostEvent(win, ResultEvent(
                id=NOTE_UPDATE_ID_A,
                data=ChangeFontColor(note_str + '\n')))

        # 闪烁窗口
        wx.PostEvent(win, ResultEvent(id=FLASH_WINDOW_ID, data=None))

        # 延时
        time.sleep(30)

    while True:

        # 调用半小时图片更新函数
        OnTimer(win, debug)
        time.sleep(15)

        # 调用控制台处理函数
        OnTimerCtrl(win, debug)
        time.sleep(15)


def OnTimer(win, debug=False):
    """
    定时器响应函数
    :return:
    """
    global last_upt_t
    upt_flag, last_upt_t = is_time_h_macd_update(last_upt_t)
    wx.PostEvent(win, ResultEvent(id=LAST_TIME_UPDATE_ID, data=last_upt_t))

    if not upt_flag:
        wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data='图片更新定时器：“小时图片”更新时间点未到！\n'))
        return

    # 清屏
    wx.PostEvent(win, ResultEvent(id=NOTE_UPDATE_ID_S, data='检测时间：' + get_current_datetime_str() + '\n\n'))

    # 生成更新的图片
    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data='开始更新小时图片...\n'))
    pic_dict = timer_update_pic('h')
    wx.PostEvent(win, ResultEvent(id=HOUR_UPDATE_ID, data=pic_dict))
    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data='小时图片更新完成！\n'))

    # 中期水平检测
    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data='开始“中期水平检测”...！\n'))
    df_level = check_stk_list_middle_level(list(set(readConfig()['buy_stk'] + readConfig()['concerned_stk'])))
    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data='“中期水平检测”完成！\n'))
    wx.PostEvent(win, ResultEvent(id=NOTE_UPDATE_ID_A, data=str(df_level) + '\n\n'))

    note_tmp = \
    """
    ----------------------------------------------------------------------------------
    小提示：
    所谓“中期水平检测”是对自己的“持仓股票”和“关注股票”的当前价格在两个月内的水平
    进行统计排名，由低到高排序，越在前面的，表示当前价格越是处于低位！
    level这一列表示处于低位的实际情况，是一个0~100的数，比如12.2表示当前价格只超过了两
    个月来12.2%的时间！
    ----------------------------------------------------------------------------------
    """ + '\n'

    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data=note_tmp))

    # 拐点检测
    for stk in list(set(readConfig()['buy_stk'] + readConfig()['concerned_stk'] + readConfig()['index_stk'])):
        hour_macd_str = checkSingleStkHourMACD_wx(stk, source='jq')
        if len(hour_macd_str):
            wx.PostEvent(win, ResultEvent(id=NOTE_UPDATE_ID_A, data=ChangeFontColor(hour_macd_str)))

    wx.PostEvent(win, ResultEvent(id=FLASH_WINDOW_ID, data=None))

    note_tmp = \
    """
    ----------------------------------------------------------------------------------
    小提示：
    所谓“拐点检测”是对自己的“持仓股票”和“关注股票”以及“三大指数”的小时级别和半
    小时级别的MACD柱子进行分析，找出“开始上涨”和“开始下跌”的情况，在控制台向用户提
    示，用户收到提示后可以查看其相应的MACD图，以便对价格走势做进一步的判断！
    ----------------------------------------------------------------------------------
    """ + '\n'

    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_A, data=note_tmp))


def ChangeFontColor(msg_str):
    """
    根据字符串内所含的字符的情况，对字符进行颜色调整，
    按照先前制定的规则，如果要修改颜色，需要将原先的字符串格式外面包一层，编程tuple格式
    即：
    ('r', msg_str)
    这种格式！r表示红色
    :param msg_str:
    :return:
    """

    # 首先判断是否为字符串格式，非字符串格式直接返回
    if isinstance(msg_str, str):

        if ('触发卖出网格' in msg_str) | ('上涨' in msg_str):
            return 'r', msg_str

        elif ('触发买入网格' in msg_str) | ('下跌' in msg_str):
            return 'g', msg_str

        else:
            return msg_str
    else:
        return msg_str


def OnTimerCtrl(win, debug=False):

    """
    定时器响应函数
    :return:
    """

    # 清屏
    wx.PostEvent(win, ResultEvent(id=MSG_UPDATE_ID_S, data='检测时间：' + get_current_datetime_str() + '\n\n'))

    # 不在交易时间不使能定时器
    if not is_in_trade_time():
        wx.PostEvent(win, ResultEvent(
            id=MSG_UPDATE_ID_A,
            data='控制台定时器：当前不属于交易时间！\n'))

        return

    buy_stk_list = list(set(readConfig()['buy_stk'] + readConfig()['index_stk']))

    if debug:
        print('OnTimerCtrl_4')

    # 局部变量
    note_list = []

    # 对股票进行检查
    for stk in buy_stk_list:
        str_gui = JudgeSingleStk(stk_code=stk, stk_amount_last=400, qq='', gui=True)

        if len(str_gui['note']):
            note_list.append(str_gui['note'])

        # 打印流水信息
        if len(str_gui['msg']):
            wx.PostEvent(win, ResultEvent(
                id=MSG_UPDATE_ID_A,
                data=str_gui['msg']))

    # 根据情况打印提示信息，并闪动
    if len(note_list):

        # 清屏
        wx.PostEvent(win, ResultEvent(
            id=NOTE_UPDATE_ID_S,
            data='检测时间：' + get_current_datetime_str() + '\n\n'))

        # 打印提示
        for note in note_list:
            wx.PostEvent(win, ResultEvent(
                id=NOTE_UPDATE_ID_A,
                data=ChangeFontColor(note)))

        # 闪动图标提醒
        wx.PostEvent(win, ResultEvent(
            id=FLASH_WINDOW_ID,
            data=None))


class MyFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, id=-1, title=title)

        # 绑定按键事件与函数
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)

        self.handle = self.GetHandle()
        self.nb = wx.Notebook(self)

        # 行信息对照表，防止贴图出错
        self.r2code = self.gen_r_to_code()
        self.index_page = [(1, 'Index'), (2, 'Buy'), (3, 'Concerned')]

        # 绑定ID与响应函数
        self.Connect(-1, -1, INIT_CPT_ID, self.OnInitPic)
        self.Connect(-1, -1, HOUR_UPDATE_ID, self.OnUpdateHourPic)
        self.Connect(-1, -1, MSG_UPDATE_ID_A, self.OnUpdateMsgTc_A)
        self.Connect(-1, -1, MSG_UPDATE_ID_S, self.OnUpdateMsgTc_S)
        self.Connect(-1, -1, NOTE_UPDATE_ID_A, self.OnUpdateNoteTc_A)
        self.Connect(-1, -1, NOTE_UPDATE_ID_S, self.OnUpdateNoteTc_S)
        self.Connect(-1, -1, LAST_TIME_UPDATE_ID, self.OnUpdateLastTime)
        self.Connect(-1, -1, FLASH_WINDOW_ID, self.FlashWindow)

        # 获取控制台panel对象
        self.nb.AddPage(MyPanelText(self.nb), "控制台")
        self.p_ctrl = self.nb.GetPage(0)

        # 更新RSV
        self.updateRSVRecord()

        # 函数外部变量
        self.last_upt_t = get_t_now()
        self.Show()

        # 启动数据处理线程，专用于处理数据，防止软件操作卡顿
        self.thread = threading.Thread(target=OnTimerWorkThread, args=(self, False))
        self.thread.start()

    def OnInitPic(self, evt):
        """
        :return:
        """

        r_temp = evt.data

        self.nb.AddPage(MyPanelGrid(self.nb, r_temp['Index']), "指数")
        self.nb.AddPage(MyPanelGrid(self.nb, r_temp['Buy']), "持仓")
        self.nb.AddPage(MyPanelGrid(self.nb, r_temp['Concerned']), "关注")
        self.Refresh()

    def OnUpdateHourPic(self, evt):

        pic_dict = evt.data

        # 更新图片
        for page in self.index_page:

            p_index = page[0]
            p_name = page[1]

            # 获取page
            p_nb = self.nb.GetPage(p_index)

            # 循环插入图片
            for k, img in pic_dict[p_name].items():
                p_nb.insert_Pic_To_Cell(img[0], 1, img[1])

        self.Refresh()

    def Change_Tc_Color(self, data, tc):
        """
        改变textctrl中字符的打印颜色
        :param data:
        :param tc:
        :return:
        """

        if isinstance(data, str):
            tc.SetDefaultStyle(wx.TextAttr(wx.LIGHT_GREY))           # 默认字体颜色为浅灰色
            return data

        elif isinstance(data, tuple):
            if data[0] is 'r':
                tc.SetDefaultStyle(wx.TextAttr(wx.RED))              # 红色字体
                return data[1]

            elif data[0] is 'g':
                tc.SetDefaultStyle(wx.TextAttr(wx.GREEN))            # 绿色字体
                return data[1]

            elif data[0] is 'y':
                tc.SetDefaultStyle(wx.TextAttr(wx.YELLOW))           # 黄色字体
                return data[1]

            else:
                tc.SetDefaultStyle(wx.TextAttr(wx.LIGHT_GREY))       # 默认字体颜色为浅灰色
                return data[1]
        else:
            tc.SetDefaultStyle(wx.TextAttr(wx.LIGHT_GREY))           # 默认字体颜色为浅灰色
            return data

    def OnUpdateNoteTc_A(self, evt):
        """
        以“追加”的方式在“提示”对话框打印字符！
        :param evt:
        :return:
        """

        # 调整字体颜色
        str_note = self.Change_Tc_Color(evt.data, self.p_ctrl.m_textCtrlNote)

        if len(str_note):
            self.p_ctrl.m_textCtrlNote.AppendText(str_note)
            # self.p_ctrl.m_textCtrlNote.AppendText('\n\n检测时间：' + get_current_datetime_str() + '\n\n')

    def FlashWindow(self, evt):
        win32gui.FlashWindowEx(self.handle, 2, 3, 400)

    def OnUpdateNoteTc_S(self, evt):
        """
        以“覆盖”的方式在“提示”对话框打印字符！
        :param evt:
        :return:
        """

        # 调整字体颜色
        str_note = self.Change_Tc_Color(evt.data, self.p_ctrl.m_textCtrlNote)

        if len(str_note):
            self.p_ctrl.m_textCtrlNote.SetValue(str_note)
            # self.p_ctrl.m_textCtrlNote.AppendText('\n\n检测时间：' + get_current_datetime_str() + '\n\n')
            # win32gui.FlashWindowEx(self.handle, 2, 3, 400)

    def OnUpdateMsgTc_A(self, evt):
        """
        更新textctrl中的文本，后缀A表示采用append（添加）的方式，而非S（覆盖）的方式
        :param evt:
        :return:
        """

        # 调整字体颜色
        str_msg = self.Change_Tc_Color(evt.data, self.p_ctrl.m_textCtrlMsg)

        if len(str_msg):
            self.p_ctrl.m_textCtrlMsg.AppendText(str_msg)
            # self.p_ctrl.m_textCtrlMsg.AppendText('\n\n检测时间：' + get_current_datetime_str() + '\n\n')

    def OnUpdateMsgTc_S(self, evt):

        # 调整字体颜色
        str_msg = self.Change_Tc_Color(evt.data, self.p_ctrl.m_textCtrlMsg)

        if len(str_msg):
            self.p_ctrl.m_textCtrlMsg.SetValue(str_msg)

    def updateRSVRecord(self):
        try:
            code_list = list(set(readConfig()['buy_stk'] + readConfig()['concerned_stk'] + readConfig()['index_stk']))

            # global  RSV_Record
            for stk in code_list:
                RSV_Record[stk] = calRSVRank(stk, 5)

        except Exception as e:
            # print(str(e))
            self.p_ctrl.m_textCtrlMsg.AppendText('RSV数据更新失败！原因：\n' + str(e) + '\n')

    def OnUpdateLastTime(self, evt):
        self.last_upt_t = evt.data

    def gen_r_to_code(self):
        r2code = copy.deepcopy(dict_stk_list)

        for page in r2code.keys():
            r2code[page] = dict(enumerate(r2code[page]))

        return r2code

    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_F1:
            print('检测到F1按下！')

            # 创建灯神，并显示
            ds = DengShen(self, '灯神')
            ds.Show()

        else:
            event.Skip()


def checkSingleStkHourMACD_wx(stk_code, source='jq'):

    df_30, df_60 = gen_hour_macd_values(stk_code, source=source, title='')

    l_60 = df_60.tail(3)['MACD'].values
    l_30 = df_30.tail(3)['MACD'].values

    if l_60[1] == np.min(l_60):

        title_str = '60分钟开始上涨'
        sts = 1
    elif l_60[1] == np.max(l_60):
        title_str = '60分钟开始下跌'
        sts = 2
    elif l_30[1] == np.max(l_30):
        title_str = '30分钟开始下跌'
        sts = 3
    elif l_30[1] == np.min(l_30):
        title_str = '30分钟开始上涨'
        sts = 4
    else:
        title_str = '当前无拐点'
        sts = 0

    # 避免重复发图！
    if stk_code in MACD_min_last.keys():
        if MACD_min_last[stk_code] != sts:
            send_pic = True
            MACD_min_last[stk_code] = sts
        else:
            send_pic = False
    else:
        send_pic = True
        MACD_min_last[stk_code] = sts

    if send_pic & (sts != 0):
        return code2name(stk_code) + '-' + title_str + '\n'
    else:
        return ''


def is_in_trade_time():
    """
    判断是否在交易时间，即
    09:30~11:30
    13:00~15:00

    :return:
    """
    r = get_current_datetime_str()
    h, m, s = r.split(' ')[1].split(':')
    t = int(h + m)
    if ((t > 930) & (t < 1130)) | ((t > 1300) & (t < 1500)):
        return True
    else:
        return False


def is_time_h_macd_update(last_upt_t):
    """
    判断是否需要更新小时macd图
    选择在
    10:00,10:30,11:00,11:30,13:00,13:30,14:00,14:30,15:00
    等几个时间点更新图片
    :param: last_upt_t 上次更新时间
    :return:
    """
    t_pot = [1000, 1030, 1100, 1130, 1330, 1400, 1430, 1500]
    t = get_t_now()

    r_judge = [(t > x) & (last_upt_t < x) for x in t_pot]

    if True in r_judge:
        return True, t
    else:
        return False, last_upt_t


if __name__ == '__main__':
    checkConfigFile()
    from DataSource.auth_info import *

    # r = get_pic_dict()
    # r = timer_update_pic('h')
    # timer_update_pic('h')

    # str_hour_macd = ''
    # for stk in list(set(readConfig()['buy_stk'] + readConfig()['concerned_stk'] + readConfig()['index_stk'])):
    #     str_hour_macd = str_hour_macd + checkSingleStkHourMACD_wx(stk, source='jq')

    app = wx.App()
    app.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)
    frame = MyFrame(None, title="魔灯-V20190919")

    frame.Show()
    app.MainLoop()
