'''
    --- updataLogs↓ ---
    v13: 解决队列过期错误: 限制 queue 大小
    v12: 限制单个文件大小 size
    v11: 增加 size 显示
    v10: 日志增加级别类型; 增加任务完成反馈
    v9: 整体文件名处理回调hander, size调大到600
    v8: 必要的文件名过滤还是要的;
    v7: 发现caption循环读取;    关闭图片模式下的caption
    v6: 发现队列仍挤了200+;     将caption 转回 hander
    v5: 发现队列拥挤;           故将'if media' 转回 hander来处理
    v4: 将文件名校验等耗时工作  转移到 worker

    --- errs↓ ---
    err1: FileReferenceExpiredError, queue领先于worker(过期,
    solution1: 限制queue大小
'''

# !/usr/bin/env python3
import difflib, os, sys, re, logging, time, asyncio
from telethon import TelegramClient, events, errors
from telethon.tl.types import MessageMediaWebPage

logname = "log"+".log" # 日志文件名
logging.basicConfig(filename = logname,level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

user = 'alias' # anything
api_id = 100001   # your telegram api id
api_hash = '100001'  # your telegram api hash
bot_token = '100001:100001'  # your bot_token
admin_id = 100001  # your chat id

add_flag = 0 # 追加模式
filter_want = ['.png','.jpg'] # 文件类型限制
max_num = 50 # 最大同时下载队列
save_path = '/usr/down/tele' # 保存路径
TIMEOUT = 10 * 60 * 60 # 下载超时
limitSize = 100 * 1024 # 大小限制
caption_flag = False # 是否获取相册标题, 视频模式可打开
RVS = False # reverse
    
#**********************************************************************************#

def overSize(msg):
    # ori/1024 = kb
    if msg.photo:
        return msg.photo.sizes[1].size/1024 > limitSize
    if msg.document:
        # 1 MB < vsize < limitSize MB 太小的不要
        vsize = msg.document.size/1024
        # print(f"return: {vsize > limitSize or vsize < 1024}, mediasize:{vsize}, size:{limitSize}")
        return vsize > limitSize or vsize < 1024

def validateTitle(title):
    r_str = r"[\/\\\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    new_title = re.sub(r_str, "_", title)  # 替换为下划线
    return new_title

# 获取相册标题
async def get_group_caption(message):
    group_caption = ""
    entity = await client.get_entity(message.to_id)
    async for msg in client.iter_messages(entity=entity, reverse=RVS, offset_id=message.id - 9, limit=10):
        if msg.grouped_id == message.grouped_id:
            if msg.text != "":
                group_caption = msg.text
                return group_caption
    return group_caption

# 获取本地时间
def get_local_time():
    return time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())

# 判断相似率 ，用于过滤标题
def get_equal_rate(str1, str2):
    return difflib.SequenceMatcher(None, str1, str2).quick_ratio()

queue = asyncio.Queue() # 待下载队列

@events.register(events.NewMessage(pattern='/start', from_users=admin_id))
async def handler(update):
    #*********************处理bot消息****************************#
    text = update.message.text.split(' ')
    end_id = 999999
    if len(text) == 1:
        await bot.send_message(admin_id, '参数错误，请按照参考格式输入:\n\n '
                                         '<i>/start https://t.me/fkdhlg 0 </i>\n\n'
                                         'Tips:如果不输入offset_id, 默认从第一 条开始下载。', parse_mode='HTML')
        return
    elif len(text) == 2:
        chat_id = text[1]
        try:
            entity = await client.get_entity(chat_id)
            chat_title = entity.title
            offset_id = 0
            await update.reply(f'开始从{chat_title}的第一条消息下载。')
        except:
            await update.reply('chat输入错误,请输入频道或群组的链接')
            return
    elif len(text) == 3:
        chat_id = text[1]
        offset_id = int(text[2])
        try:
            entity = await client.get_entity(chat_id)
            chat_title = entity.title
            await update.reply(f'开始从{chat_title}的第{offset_id}条消息下载。')
        except:
            await update.reply('chat输入错误,请输入频道或群组的链接')
            return
    elif len(text) == 4:
        chat_id = text[1]
        offset_id = int(text[2])
        end_id = int(text[3])
        try:
            entity = await client.get_entity(chat_id)
            chat_title = entity.title
            await update.reply(f'开始从{chat_title}的第{offset_id}条消息下载。')
        except:
            await update.reply('chat输入错误,请输入频道或群组的链接')
            return
    else:
        await bot.send_message(admin_id, '参数错误，请按照参考格式输入:\n\n '
                                         '<i>/start https://t.me/fkdhlg 0 </i>\n\n'
                                         'Tips:如果不输入offset_id,默认从第一 条开始下载。', parse_mode='HTML')
        return
        #*********************处理bot消息****************************#

    if chat_title:
        logging.info(f'{get_local_time()} - 开始下载：{chat_title}({entity.id}) - {offset_id}')
        print(f'{get_local_time()} - 开始下载：{chat_title}({entity.id}) - {offset_id}')
        last_msg_id = 0

        async for message in client.iter_messages(entity, offset_id=offset_id, reverse=RVS, limit=None):
            if message.media:
                if caption_flag:
                    caption = await get_group_caption(message) if (
                    message.grouped_id and message.text == "") else message.text
                else:
                    caption = message.text

                # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长 导致的错误
                caption = "" if caption == "" else f'{validateTitle(caption)}'[:30]

                #### 文件名处理
                file_name = ''
                if message.document:
                    if type(message.media) == MessageMediaWebPage:
                        continue
                    if message.media.document.mime_type == "image/webp":
                        continue
                    if message.media.document.mime_type == "application/x-tgsticker":
                        continue
                    for i in message.document.attributes:
                        try:
                            file_name = i.file_name
                        except:
                            continue
                    ## 视频文件
                    msgSize = str(int(message.document.size/1024/1024)) + "MB"
                    if file_name == '':
                        file_name = f'{message.id} - {caption}.{message.document.mime_type.split("/")[-1]}'
                    else:
                        # 如果文件名中已经包含了标题，则过滤标题
                        if get_equal_rate(caption, file_name) > 0.6:
                            caption = ""
                        file_name = f'{message.id} - {caption}{file_name}'
                elif message.photo:
                    msgSize = str(int(message.photo.sizes[1].size/1024)) + "KB"
                    file_name = f'{message.id} - {caption}{message.photo.id}.jpg'
                else:
                    continue
                ##

                ## 过滤特定格式文件
                fmt=file_name.split('.')[-1]
                if not fmt in filter_want:
                    print("[skip]" + fmt + " " + str(message.id))
                    logging.info("[skip]" + fmt + " " + str(message.id))
                    continue

                ## 限制过大和过小的文件
                if overSize(message):
                    msg_oversize = f"[skip]oversize, id:{message.id}, size: {msgSize}"
                    print(msg_oversize)
                    logging.info(msg_oversize)
                    continue

                # 文件名处理
                dirname = validateTitle(f'{chat_title}({entity.id})')
                datetime_dir_name = message.date.strftime("%Y年%m月")
                file_save_path = os.path.join(save_path, dirname, datetime_dir_name)
                #file_save_path = os.path.join(save_path, dirname)
                if not os.path.exists(file_save_path):
                    os.makedirs(file_save_path)
                # 判断文件是否在本地存在，如果存在，则移除重新下载
                if file_name in os.listdir(file_save_path):
                    if add_flag:
                        continue
                    else:
                        os.remove(os.path.join(file_save_path, file_name))

                ## 避免队列太长，等待超时
                waitWarn = True
                while queue.qsize() >= max_num:
                    if waitWarn:
                        msg_overQueue = f"..[wait] task Queue is full, waitting..."
                        print(msg_overQueue)
                        logging.info(msg_overQueue)
                        waitWarn = False
                    await asyncio.sleep(5)

                #**************** ↓核心部分↓ ******************#
                await queue.put((message, chat_title, entity, file_name, msgSize))

                print(f">>[putQue] title:{entity.id}, msgid:{message.id}, qSize:{queue.qsize()}")
                logging.info(f">>[putQue] title:{entity.id}, msgid:{message.id}, qSize:{queue.qsize()}")
                if message.id == end_id:
                    break
                last_msg_id = message.id

        await bot.send_message(admin_id, f'{chat_title} all message added to task queue, last message is: {last_msg_id}')
        print(admin_id, f'{chat_title} all message added to task queue, last message is: {last_msg_id}')

async def dlworker(name):
    while True:
        queue_item = await queue.get()

        message = queue_item[0]
        chat_title = queue_item[1]
        entity = queue_item[2]
        file_name = queue_item[3]
        msgSize = queue_item[4]

        dirname = validateTitle(f'{chat_title}({entity.id})')
        datetime_dir_name = message.date.strftime("%Y年%m月")
        file_save_path = os.path.join(save_path, dirname, datetime_dir_name)

        print(f"<<[start {name}] title:{entity.id}, msgid:{message.id}, size:{msgSize}")
        logging.info(f"<<[start {name}] title:{entity.id}, msgid:{message.id}, size:{msgSize}")

        #### 核心部分 ####
        try:
            loop = asyncio.get_event_loop()
            task = loop.create_task(client.download_media(
                message, os.path.join(file_save_path, file_name)))
            await asyncio.wait_for(task, timeout=TIMEOUT)

            msg_dlsuc=f'--[dlsuc] Title:{entity.id}, Msgid:{message.id}, size:{msgSize}'
            print(msg_dlsuc)
            logging.info(msg_dlsuc)
        #### 核心部分 ####

        except (errors.FileReferenceExpiredError, asyncio.TimeoutError):
            if overSize(message):
                print("   too big,skip")
                logging.info("   too big,skip")
                continue
            print(f'{get_local_time()} - msgid:{message.id} 出现异常，重新尝试下载！')
            logging.info(f'{get_local_time()} - msgid:{message.id} 出现异常，重新尝试 下载！')
            async for new_message in client.iter_messages(entity=entity, offset_id=message.id - 1, reverse=RVS,limit=1):
                await queue.put((new_message, chat_title, entity, file_name))

        except Exception as e:
            print(f"{get_local_time()} - msgid:{message.id} {file_name} {e.__class__} {e}")
            logging.info(f"{get_local_time()} - msgid:{message.id} {file_name} {e.__class__} {e}")
            await bot.send_message(admin_id, f'{e.__class__}!\n\n{e}\n\n{file_name}')

        finally:
            queue.task_done()
            # print(f"task done, queueSize: {queue.qsize()}")
            # logging.info(f"task done, queueSize: {queue.qsize()}")
        #if(queue.empty()):
        #    await bot.send_message(admin_id, f'下载完毕，最后一条为：{chat_title}_{last_msg_id}')
        #    print(admin_id, f'下载完毕，最后一条为：{chat_title}_{last_msg_id}')
        #    logging.info(admin_id, f'下载完毕，最后一条为：{chat_title}_{last_msg_id}')
        # print("end of WHILE loop"+name)


if __name__ == '__main__':

    # 通过 id 和 token 等启动 bot 机器人
    bot = TelegramClient('telegram_channel_downloader_bot', api_id, api_hash).start(bot_token=str(bot_token))
    client = TelegramClient('telegram_channel_downloader', api_id, api_hash).start()
    bot.add_event_handler(handler)

    # 任务列表
    tasks = []
    try:
        # 启动 max_num 个 task
        for i in range(max_num):
            loop = asyncio.get_event_loop()
            task = loop.create_task(dlworker(f'worker-{i}'))
            tasks.append(task)
        print('Successfully started (Press Ctrl+C to stop)')
        logging.info('Successfully started (Press Ctrl+C to stop)')
        client.run_until_disconnected()

    # 确保程序正确终止
    finally:
        for task in tasks:
            task.cancel()
        client.disconnect()
        print('Stopped!')
        logging.info("stoped!")