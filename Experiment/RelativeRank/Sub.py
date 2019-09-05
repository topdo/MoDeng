# encoding=utf-8
import jqdatasdk
import jqdatasdk as jq
import talib
import tushare as ts
import os

import math

# from AutoDailyOpt.opt_info_input import localDBInfo
from AutoDailyOpt.p_diff_ratio_last import MACD_min_last, MACD_min_History, M_Data
# from JQData_Test.JQ_Industry_Analysis_Sub import *
# from MACD_Stray_Analysis.Demo1 import week_macd_stray_judge

from AutoDailyOpt.SeaSelect.stk_pool import stk_pool
from Config.GlobalSetting import localDBInfo
from SDK.DBOpt import genDbConn
from SDK.MyTimeOPT import get_current_date_str, add_date_str
from Config.AutoStkConfig import stk_list, SeaSelectDataPWD, LastScale
from SDK.PlotOptSub import addXticklabel_list
from SDK.shelfSub import shelveP, shelveL
from SendMsgByQQ.QQGUI import send_qq
from pylab import *

import pandas as pd
import copy
import numpy as np

from SendMsgByQQ.SendPicByQQ import send_pic_qq



"""
计算相对排名

"""


def relativeRank(v_total, v_now):
    """
    计算相对排名子函数
    :param list:
    :return:
    """
    if isinstance(v_total, pd.Series):
        v_total = list(v_total.values)
    else:
        v_total = list(v_total)

    # 去除空值
    v_total = list(filter(lambda x: not pd.isnull(x), v_total))

    if pd.isnull(v_now) | (len(v_total) == 0):
        return np.nan

    # 计算排名
    v_bigger_amount = len(list(filter(lambda x: x > v_now, v_total)))

    return v_bigger_amount/(len(v_total)+0.000001)*100


# def calSingleStkRank(m_days, stk_code, days_length, p_now):
#
#     """
#     :param m_days:              ？天均线的离心度
#     :param stk_code:
#     :param days_length:         在？天内进行排名
#     :return:
#     """
#
#     df = ts.get_k_data(stk_code, start=add_date_str(get_current_date_str(), -1*days_length*1.8))
#
#     if len(df) < days_length*0.8:
#         print('函数 calSingleStkRank: 该stk历史数据不足！')
#         return -1
#
#     # 测试相对均值偏移度
#     df['m9'] = df['close'].rolling(window=m_days).mean()
#     df['diff_m9'] = df.apply(lambda x: (x['close'] - x['m9']), axis=1)
#
#     """
#     df.plot('date', ['close', 'diff_m9', 'rank'], subplots=True)
#     """
#
#     # 给m9打分
#     return relativeRank(df['diff_m9'], p_now)


def get_k_data_JQ(stk_code, count=None, start_date=None, end_date=get_current_date_str(), freq='daily'):
    """
    使用JQData来下载stk的历史数据
    :param stk_code:
    :param amount:
    :return:
    """
    if stk_code in ['sh', 'sz', 'cyb']:

        stk_code_normal = {
            'sh': '000001.XSHG',
            'sz': '399001.XSHE',
            'cyb': '399006.XSHE'
        }[stk_code]
        df = jqdatasdk.get_price(stk_code_normal, frequency=freq, count=count, start_date=start_date,
                                 end_date=end_date)
    else:
        df = jqdatasdk.get_price(jqdatasdk.normalize_code(stk_code), frequency=freq, count=count,
                                 end_date=end_date, start_date=start_date)

    df['datetime'] = df.index
    df['date'] = df.apply(lambda x: str(x['datetime'])[:10], axis=1)

    return df


def ts_code_normalize(code):
    """
    规整tushare 代码
    :return:
    """

    if code in ['sh', 'sz', 'cyb']:

        return {
            'sh': '000001.SH',
            'sz': '399001.SZ',
            'cyb': '399006.SZ'
        }[code]

    if code[0] == '6':
        code_normal = code+'.SH'
    else:
        code_normal = code+'.SZ'

    return code_normal


def my_pro_bar(stk_code, start, end=get_current_date_str(), adj='qfq', freq='D'):

    df = ts.pro_bar(ts_code=ts_code_normalize(stk_code), start_date=start, end_date=end, adj=adj, freq=freq)
    if freq == 'D':
        df = df.rename(columns={'trade_date': 'date'}).sort_values(by='date', ascending=True)
        df['date'] = df.apply(lambda x: x['date'][:4]+'-'+x['date'][4:6]+'-'+x['date'][6:], axis=1)
    elif 'min' in freq:
        df = df.rename(columns={'trade_time': 'time'}).sort_values(by='time', ascending=True)
    return df


def saveStkMRankHistoryData2Global(stk_code, history_days, m_days, save_dir):
    """
    保存stk的历史数据，用来实时计算均线离心度分数，需要存历史数据，尽量不要用！

    :param stk_code:
    :param history_days:
    :param save_dir:        './M_data/'
    :return:
    """

    df = get_k_data_JQ(stk_code, 400, end_date=get_current_date_str())

    if len(df) < history_days*0.8:
        print('函数 calSingleStkRank: 该stk历史数据不足！')
        return -1

    # 测试相对均值偏移度
    df['m9'] = df['close'].rolling(window=m_days).mean()
    df['diff_m9'] = df.apply(lambda x: (x['close'] - x['m9'])/x['close'], axis=1)

    df = df.dropna()

    dict_restore = {
        'stk_code': stk_code,
        'history_M_diverge_data': list(df['diff_m9'].values),
        'latest_data': list(df.tail(m_days-1)['close'].values),
        'update_date': df.tail(1)['date'].values[0]
    }

    # global M_Data

    M_Data[stk_code] = dict_restore

    # shelveP(
    #     data=dict_restore,
    #     saveLocation=save_dir,
    #     fileName=stk_code+'_M'+str(m_days))


def saveStkMRankHistoryData(stk_code, history_days, m_days, save_dir):
    """
    保存stk的历史数据，用来实时计算均线离心度分数，需要存历史数据，尽量不要用！

    :param stk_code:
    :param history_days:
    :param save_dir:        './M_data/'
    :return:
    """

    df = get_k_data_JQ(stk_code, 400)

    if len(df) < history_days*0.8:
        print('函数 calSingleStkRank: 该stk历史数据不足！')
        return -1

    # 测试相对均值偏移度
    df['m9'] = df['close'].rolling(window=m_days).mean()
    df['diff_m9'] = df.apply(lambda x: (x['close'] - x['m9'])/x['close'], axis=1)

    df = df.dropna()

    dict_restore = {
        'stk_code': stk_code,
        'history_M_diverge_data': list(df['diff_m9'].values),
        'latest_data': list(df.tail(m_days-1)['close'].values),
        'update_date': df.tail(1)['date'].values[0]
    }

    shelveP(
        data=dict_restore,
        saveLocation=save_dir,
        fileName=stk_code+'_M'+str(m_days))


def calRealtimeRank_JQ_Direct(stk_code, M_days):
    """
    不使用历史数据，现场下载现场计算
    :param stk_code:
    :param M_days:
    :return:
    """


def get_RT_price(stk_code, source='jq'):

    if source == 'jq':
        # 使用聚宽数据接口替代
        if stk_code in ['sh', 'sz', 'cyb']:
            stk_code_normal = {
                'sh': '000001.XSHG',
                'sz': '399001.XSHE',
                'cyb': '399006.XSHE'
            }[stk_code]

        else:
            stk_code_normal = jq.normalize_code(stk_code)

        current_price = float(
            jq.get_price(stk_code_normal, count=1, end_date=get_current_date_str())['close'].values[0])

    elif source == 'ts':
        # 获取实时价格
        current_price = float(ts.get_realtime_quotes(stk_code)['price'].values[0])

    return current_price


def calRealtimeRankWithGlobal(stk_code):
    """
    计算一只stk的离心度名次,
    从全局变量中读取历史数据！
    :param stk_code:
    :param M_days:
    :param history_data_dir: './M_data/'
    :return: 分数，9日数据， 当前price
    """

    # 加载数据测试
    if stk_code in M_Data.keys():
        dict = M_Data[stk_code]
    else:
        print('函数 calRealtimeRankWithGlobal：历史数据 M_Data 中没有'+stk_code+'的数据！')
        return -1, [], np.nan, []

    if stk_code not in ['sh', 'sz', 'cyb']:
        try:
            current_price = get_RT_price(stk_code, source='ts')
        except:
            current_price = get_RT_price(stk_code, source='jq')
    else:
        current_price = get_RT_price(stk_code, source='jq')

    # 计算实时偏离度
    list_history = copy.deepcopy(dict['latest_data'])
    list_history.append(current_price)
    M_diff = (current_price - np.mean(list_history))/current_price

    # 计算排名
    return relativeRank(dict['history_M_diverge_data'], M_diff), list_history, current_price, dict['update_date']


def calRealtimeRank(stk_code, M_days, history_data_dir):
    """
    计算一只stk的离心度名次,
    需要保存历史数据，操作复杂，尽量不要用！
    :param stk_code:
    :param M_days:
    :param history_data_dir: './M_data/'
    :return: 分数，9日数据， 当前price
    """

    # 加载数据测试
    dict = shelveL(
        loadLocation=history_data_dir,
        fileName=stk_code+'_M'+str(M_days))

    if stk_code not in ['sh', 'sz', 'cyb']:
        try:
            current_price = get_RT_price(stk_code, source='ts')
        except:
            current_price = get_RT_price(stk_code, source='jq')
    else:
        current_price = get_RT_price(stk_code, source='jq')

    # 计算实时偏离度
    list_history = dict['latest_data']
    list_history.append(current_price)
    M_diff = (current_price - np.mean(list_history))/current_price

    # 计算排名
    return relativeRank(dict['history_M_diverge_data'], M_diff), list_history, current_price, dict['update_date']


def checkDivergeLowLevel():
    """
    供定时器调用的回调函数，按频率检查关心的stk的，对高于80分的进行提示
    :return:
    """
    checkDivergeLowLevel_Sub(stk_list, 'stk_list', 80, desk=1, qq_win_name='影子2', hist_data_dir=SeaSelectDataPWD+'/stk_list_data/')
    checkDivergeLowLevel_Sub(stk_list, 'stk_list', 100, qq_win_name='影子', hist_data_dir=SeaSelectDataPWD+'/stk_list_data/', logic=False)


def get_current_price_JQ(stk_code):

    # 使用聚宽数据接口替代
    if stk_code in ['sh', 'sz', 'cyb']:
        stk_code_normal = {
            'sh': '000001.XSHG',
            'sz': '399001.XSHE',
            'cyb': '399006.XSHE'
        }[stk_code]

    else:
        stk_code_normal = jq.normalize_code(stk_code)

    current_price = float(jq.get_price(stk_code_normal, count=1, end_date=get_current_date_str())['close'].values[0])

    return current_price


def updateConcernStkMData():
    """
    定时器定时调用，更新各stk的M离心度历史数据
    :return:
    """

    for stk in stk_list:
        saveStkMRankHistoryData2Global(stk_code=stk, history_days=400, m_days=9, save_dir=SeaSelectDataPWD+'/stk_list_data/')
        send_qq('影子', '更新' + stk + '离心度历史数据成功！')



def initScale(stk_list, list_name):
    """

    :param stk_list:
    :return:
    """

    shelveP(dict([(x, -1) for x in stk_list]), LastScale, list_name)


def loadLastScale(list_name):
    """

    :param list_name:
    :return:
    """

    return shelveL(LastScale, list_name)


def considerMainIndex(stk_code, r, threshold_index=80):
    """
    考虑mainIndex之后的阈值
    :return:
    """
    if stk_code in ['cyb', 'sh', 'sz']:
        if r > threshold_index:
            return True
        else:
            return False

    # 获取main_index指数：
    r_main_index = dict([(x, (calRealtimeRankWithGlobal(stk_code=x)[0])) for x in ['sh', 'sz', 'cyb']])

    if stk_code[:3] == '000':
        main_index = r_main_index['sz']

    elif stk_code[:2] == '60':
        main_index = r_main_index['sh']

    else:
        main_index = r_main_index['cyb']

    if (r > 98) | ((r > 94) & (main_index > 50)) | ((r > 85) & (main_index > 80)):
        return True
    else:
        return False


def checkDivergeLowLevel_Sub(stk_list, stk_list_name, scale_threshold, hist_data_dir, qq_win_name, desk=2, logic=True):

    """

    :param stk_list:
    :param stk_list_name:
    :param scale_threshold:
    :param hist_data_dir:
    :param desk:
    :param logic:   为真时，大于阈值会触发，为假时，小于阈值会触发
    :return:
    """

    # 判断是否存在上次分数，存在则加载，否则初始化一个
    if os.path.exists(LastScale+stk_list_name+'.dat'):
        lastscale_stk_pool = loadLastScale(stk_list_name)
    else:
        initScale(stk_list, stk_list_name)
        lastscale_stk_pool = loadLastScale(stk_list_name)

    for stk in stk_list:

        r, history_data, p_now, update_date = calRealtimeRankWithGlobal(stk_code=stk)

        # 生成语言描述
        if (r-lastscale_stk_pool[stk]) > 0:
            note = '分数上涨'+'%0.1f' % (r-lastscale_stk_pool[stk])
        else:
            note = '分数下落'+'%0.1f' % (r - lastscale_stk_pool[stk])

        if logic:
            if considerMainIndex(stk, r):
                if math.fabs(r-lastscale_stk_pool[stk]) > desk:

                    # 更新上次分数
                    lastscale_stk_pool[stk] = r

                    send_qq(qq_win_name,
                            'Attention：\n' + stk + note +
                            '\nscore：'+str('%0.2f') % r +
                            '\np_now:' + str(p_now) +
                            '\nhistory:' + str(history_data) +
                            '\nupdate_date:' + str(update_date))

                    shelveP(lastscale_stk_pool, LastScale, stk_list_name)
                else:
                    print('与上次命令相同！')
            else:
                print(stk+'分数处于正常状态！分数为：'+str('%0.2f') % r)
        else:
            if r < scale_threshold:
                if math.fabs(r-lastscale_stk_pool[stk]) > desk:

                    # 更新上次分数
                    lastscale_stk_pool[stk] = r

                    send_qq(qq_win_name,
                            'Attention：\n' + stk + note +
                            '\nscore：' + str('%0.2f') % r +
                            '\np_now:' + str(p_now) +
                            '\nhistory:' + str(history_data) +
                            '\nupdate_date:' + str(update_date))

                    shelveP(lastscale_stk_pool, LastScale, stk_list_name)
                else:
                    print('与上次命令相同！')
            else:
                print(stk + '分数处于正常状态！分数为：' + str('%0.2f') % r)


def checkDivergeLowLevel_Sea():

    """
    供定时器调用的回调函数，按频率检查关心的stk的，对高于80分的进行提示
    :return:
    """
    checkDivergeLowLevel_Sub(stk_pool, 'stk_pool', 94, hist_data_dir=SeaSelectDataPWD+'/stk_pool_data/', qq_win_name='影子')


def updateConcernStkMData_Sea():
    """
    定时器定时调用，更新各stk的M离心度历史数据
    :return:
    """
    try:
        for stk in stk_pool:
            saveStkMRankHistoryData2Global(stk_code=stk, history_days=400, m_days=9, save_dir=SeaSelectDataPWD+'/stk_pool_data/')
            send_qq('影子', '更新' + stk + '离心度历史数据成功！')
    except:
        send_qq('影子', '更新离心度历史数据失败！')


def updateMACDHistory():
    """
    更新当前正在交易的stk的小时和半小时macd历史数据
    :return:
    """
    (conn_opt, engine_opt) = genDbConn(localDBInfo, 'stk_opt_info')
    df = pd.read_sql(con=conn_opt, sql='select * from now')

    if not df.empty:
        for idx in df.index:
            stk_code = df.loc[idx, 'stk_code']
            updateSingleMacdHistory(stk_code, MACD_min_History)

    conn_opt.close()


def updateSingleMacdHistory(stk_code, history_dict):
    """
    更新单只stk的小时和半小时macd历史数据
    :return:
    """
    if stk_code not in history_dict.keys():
        # df_30 = my_pro_bar(stk_code, start=add_date_str(get_current_date_str(), -200), freq='30min')
        df_30 = get_k_data_JQ(stk_code, start_date=add_date_str(get_current_date_str(), -200), freq='30m')

        df_30['MACD'], _, _ = talib.MACD(df_30.close,
                                            fastperiod=12, slowperiod=26,
                                            signalperiod=9)

        df_60 = get_k_data_JQ(stk_code, start_date=add_date_str(get_current_date_str(), -200), freq='60m')

        df_60['MACD'], _, _ = talib.MACD(df_60.close,
                                            fastperiod=12, slowperiod=26,
                                            signalperiod=9)

        df_30 = df_30.dropna()
        df_60 = df_60.dropna()

        history_dict[stk_code] = {
            'min30': df_30['close'],
            'min60': df_60['close']
        }

def checkHourMACD_callback():

    (conn_opt, engine_opt) = genDbConn(localDBInfo, 'stk_opt_info')
    df = pd.read_sql(con=conn_opt, sql='select * from now')

    for code in ['sh', 'sz', 'cyb']:
        checkSingleStkHourMACD(code)

    if not df.empty:
        for idx in df.index:
            stk_code = df.loc[idx, 'stk_code']
            checkSingleStkHourMACD(stk_code)
    conn_opt.close()


def sendHourMACDToQQ(stk_code, qq, source='jq'):
    if source == 'jq':
        df_30 = get_k_data_JQ(stk_code, start_date=add_date_str(get_current_date_str(), -20), end_date=add_date_str(get_current_date_str(), 1), freq='30m')
        df_60 = get_k_data_JQ(stk_code, start_date=add_date_str(get_current_date_str(), -20), end_date=add_date_str(get_current_date_str(), 1), freq='60m')
    elif source == 'ts':
        df_30 = my_pro_bar(stk_code, start=add_date_str(get_current_date_str(), -20), freq='30min')
        df_60 = my_pro_bar(stk_code, start=add_date_str(get_current_date_str(), -20), freq='60min')

    # 去掉volume为空的行
    df_30 = df_30.loc[df_30.apply(lambda x: not (x['volume'] == 0), axis=1), :]
    df_60 = df_60.loc[df_60.apply(lambda x: not (x['volume'] == 0), axis=1), :]

    df_30['MACD'], _, _ = talib.MACD(df_30.close,
                                     fastperiod=12, slowperiod=26,
                                     signalperiod=9)

    df_60['MACD'], _, _ = talib.MACD(df_60.close,
                                     fastperiod=12, slowperiod=26,
                                     signalperiod=9)

    # 生成图片
    df_30 = df_30.dropna()
    df_60 = df_60.dropna()

    fig, ax = plt.subplots(ncols=1, nrows=4)

    ax[0].plot(range(0, len(df_30)), df_30['close'], 'g*--', label='close_30min')
    ax[1].bar(range(0, len(df_30)), df_30['MACD'], label='macd_30min')
    ax[2].plot(range(0, len(df_60)), df_60['close'], 'g*--', label='close_60min')
    ax[3].bar(range(0, len(df_60)), df_60['MACD'], label='macd_60min')

    # 设置下标
    ax[1] = addXticklabel_list(
        ax[1],
        list([str(x)[-11:-3] for x in df_30['datetime']]),
        30, rotation=45)

    ax[3].set_xticks(list(range(0, len(df_60['datetime']))))
    ax[3].set_xticklabels(list([str(x)[-11:-3] for x in df_60['datetime']]), rotation=45)

    for ax_sig in ax:
        ax_sig.legend(loc='best')
    plt.title(stk_code)
    fig.tight_layout()
    plt.subplots_adjust(wspace=0, hspace=1)  # 调整子图间距

    send_pic_qq(qq, fig)
    plt.close()


def checkSingleStkHourMACD(stk_code, source='jq'):
    if source == 'jq':
        df_30 = get_k_data_JQ(stk_code, start_date=add_date_str(get_current_date_str(), -20), freq='30m')
        df_60 = get_k_data_JQ(stk_code, start_date=add_date_str(get_current_date_str(), -20), freq='60m')
    elif source == 'ts':
        df_30 = my_pro_bar(stk_code, start=add_date_str(get_current_date_str(), -20), freq='30min')
        df_60 = my_pro_bar(stk_code, start=add_date_str(get_current_date_str(), -20), freq='60min')

    # 去掉volume为空的行
    df_30 = df_30.loc[df_30.apply(lambda x: not (x['volume'] == 0), axis=1), :]
    df_60 = df_60.loc[df_60.apply(lambda x: not (x['volume'] == 0), axis=1), :]

    df_30['MACD'], _, _ = talib.MACD(df_30.close,
                                     fastperiod=12, slowperiod=26,
                                     signalperiod=9)

    df_60['MACD'], _, _ = talib.MACD(df_60.close,
                                     fastperiod=12, slowperiod=26,
                                     signalperiod=9)

    l_60 = df_60.tail(3)['MACD'].values
    l_30 = df_30.tail(3)['MACD'].values

    print('函数 checkSingleStkHourMACD：'+stk_code+':\n30min:'+str(l_30)+'\n60min:'+str(l_60)+'\n')

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

    print('函数 checkSingleStkHourMACD：' + stk_code + ':\nsend_pic标志位:' + str(send_pic) + '\nsts标志位:' + str(sts) + '\n')

    # 生成图片
    df_30 = df_30.dropna()
    df_60 = df_60.dropna()

    fig, ax = subplots(ncols=1, nrows=4)

    ax[0].plot(range(0, len(df_30)), df_30['close'], 'g*--', label='close_30min')
    ax[1].bar(range(0, len(df_30)), df_30['MACD'], label='macd_30min')
    ax[2].plot(range(0, len(df_60)), df_60['close'], 'g*--', label='close_60min')
    ax[3].bar(range(0, len(df_60)), df_60['MACD'], label='macd_60min')

    for ax_sig in ax:
        ax_sig.legend(loc='best')
    plt.title(stk_code + '-' + title_str)

    if send_pic & (sts != 0):
        send_pic_qq('影子', fig)

    # send_pic_qq('影子', fig)
    plt.close()


if __name__ == '__main__':

    from DataSource.auth_info import *

    sendHourMACDToQQ('300508', '影子', source='jq')
    # updateConcernStkMData()

    # initScale(stk_pool, 'stk_pool')
    # r = getMDataPWD()

    # lastscale_stk_pool = loadLastScale('stk_pool')

    # updateConcernStkMData_Sea()
    # checkDivergeLowLevel_Sea()

    ts.set_token('7cb80219c0eec2cfee6608247e485025445f21017732a729d6f96345')
    from DataSource.auth_info import *



    stk_code = '300508'
    history_dict = MACD_min_History

    df_30 = my_pro_bar(stk_code, start=add_date_str(get_current_date_str(), -20), freq='30min')

    df_30['MACD'], _, _ = talib.MACD(df_30.close,
                                        fastperiod=12, slowperiod=26,
                                        signalperiod=9)

    df_60 = my_pro_bar(stk_code, start=add_date_str(get_current_date_str(), -20), freq='60min')

    df_60['MACD'], _, _ = talib.MACD(df_60.close,
                                        fastperiod=12, slowperiod=26,
                                        signalperiod=9)

    l_60 = df_60.tail(3)['MACD'].values
    l_30 = df_30.tail(3)['MACD'].values

    if l_60[1] == np.min(l_60):
        title_str = '60分钟开始上涨'
        send_pic = True
    elif l_60[1] == np.max(l_60):
        title_str = '60分钟开始下跌'
        send_pic = True
    elif l_30[1] == np.max(l_30):
        title_str = '30分钟开始下跌'
        send_pic = True
    elif l_30[1] == np.min(l_30):
        title_str = '30分钟开始上涨'
        send_pic = True
    else:
        send_pic = False

    if send_pic:

        fig, ax = subplots(ncols=1, nrows=4)

        ax[0].plot(range(0, len(df_30)), df_30['close'], 'g*--', label='close_30min')
        ax[1].bar(range(0, len(df_30)), df_30['MACD'], label='macd_30min')
        ax[2].plot(range(0, len(df_60)), df_60['close'], 'g*--', label='close_60min')
        ax[3].bar(range(0, len(df_60)), df_60['MACD'], label='macd_60min')

        plt.title(stk_code + title_str)
        send_pic_qq('影子2', fig)
        plt.close()


    end = 0