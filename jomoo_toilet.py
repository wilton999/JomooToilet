# -*- coding: utf-8 -*-
"""九牧智联马桶 ZS781J 控制工具（协议逆向自微信小程序「九牧智联」ToiletController.js）

帧格式(F3F4 族, 已实测):
  10字节开关: F3 F4 06 92 21 1F <cmd> <val> <校验> FC   (1F 动作)
  19字节设置/动作: F3 F4 0F 92 21 <code> <状态位...> <校验> FC
  校验 = 从长度字节到校验位前 全部求和 & 0xFF

用法:
  (默认自动扫描名字以 JOMOO_SMART 开头的设备；多台时选信号最强的)
  (首次连上后会把设备地址记录到脚本目录的 toilet_mac.txt，之后启动直接连它，
   省去扫描；删除该文件即可重新扫描。该文件含你的设备地址，请勿提交到公开仓库)
  (也可用环境变量指定地址: PowerShell 里 $env:JOMOO_MAC = "AA:BB:CC:DD:EE:FF")
  python jomoo_toilet.py scan                  只扫描（列出找到的 JOMOO 设备）
  python jomoo_toilet.py listen [秒]           监听所有通知(默认10秒)
  python jomoo_toilet.py query                 查询马桶状态
  python jomoo_toilet.py raw [resp] [ffe1|f001] <hex...>   发原始帧

开关类:
  foot on|off                脚感
  uv on|off                  水路UV杀菌
  atmo on|off                氛围灯
  atmo-mode <模式>           氛围灯(带模式)
  bubble on|off              自动发泡
  openbubble on|off          开圈发泡
  bubblerun                  立即启动魔力泡
  prewet on|off              预湿润
  closeflush on|off          关盖冲厕
  smallflush on|off          自动小冲
  closesmallflush on|off     关盖自动小冲
  filter on|off              滤芯提醒(on=复位并开启, off=关闭)
  aivoice on|off             AI语音
  petwash on|off             宠物清洗
  selfclean on|off           自清洁(立即)
  regularselfclean on|off [档]  定期自清洁
  nozzledry on|off           喷杆干燥
  autonozzledry on|off       自动喷杆干燥
  sens 0|1                   翻盖灵敏度(0/1)
  dist <数值>                翻盖感应距离
  bright <数值>              夜灯亮度
  strongdry <数值>           强力烘干(默认0x18|风温档)
  brushtime <数值>           刷圈发泡时间档
  liftclean                  喷杆清洗
  liquidbox                  加液盒
  redblue <模式> <红> <蓝>   红蓝光参数
  forceflush                 强制冲刷
  unblock                    解堵(强制冲刷2)

动作(19字节, 自动先读状态):
  act <码或简写>
    0停止 2四季温感 4暖风 5移动暖风/按摩 6强弱按摩 7自动妇洗 8臀洗
    9喷嘴自洁 10通便 11妇洗 12自动臀洗 14大冲 15小冲 16关盖关圈
    17开盖关圈 18智能除臭 19开盖开圈 22更换喷嘴 24位置同步 25设置同步 29坐浴
  简写: bigflush smallflush2 cover-close cover-open cover-openring deodorize
        wash-hip wash-woman wash-auto-hip wash-auto-woman dry defecate sitz stop

设置(19字节, 先读状态再改):
  set <键> <值>
    键: autoflush autocover gesture autoflush2 nightlight smartlight savepower
        seat water air windspeed hipnozzle hippress widewash
    值: on/off 或数字
"""
import asyncio
import os
import sys

DEVICE_NAME_PREFIX = "JOMOO_SMART"
GOODIX_MANUFACTURER_ID = 0x0211
TOILET_MAC = os.environ.get("JOMOO_MAC", "").strip() or None
MAC_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toilet_mac.txt")


def load_cached_mac():
    try:
        with open(MAC_CACHE_FILE, "r", encoding="utf-8") as f:
            mac = f.read().strip()
        return mac or None
    except OSError:
        return None


def save_cached_mac(mac):
    try:
        with open(MAC_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(mac + "\n")
    except OSError as e:
        print("警告: 无法写入 MAC 记录:", e)
WRITE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
NOTIFY_UUIDS = [
    "0000ffe1-0000-1000-8000-00805f9b34fb",
    "00010203-0405-0607-0809-0a0b0c0d2b12",
    "0000f002-0000-1000-8000-00805f9b34fb",
]
BLE_ADDR = 0x92
TOILET_ADDR = 0x21

state = {}


def hexs(b):
    return " ".join(f"{x:02X}" for x in b)


def finish(fr):
    fr.append(sum(fr[2:]) & 0xFF)
    fr.append(0xFC)
    return bytes(fr)


def frame_1f(cmd, *vals):
    fr = [0xF3, 0xF4, 0, BLE_ADDR, TOILET_ADDR, 0x1F, cmd, *vals]
    fr[2] = len(fr) + 2 - 4
    return finish(fr)


def frame_19(code):
    b6 = (state.get("water", 0) << 4) | (state.get("autocover", 0) << 3) \
        | (state.get("gesture", 0) << 2) | (state.get("autoflush", 0) << 1) \
        | state.get("nightlight", 0)
    b7 = (state.get("savepower", 0) << 7) | (state.get("hipnozzle", 0) << 4) \
        | state.get("seat", 0)
    b8 = (state.get("smartlight", 0) << 7) | (state.get("hippress", 0) << 4) \
        | state.get("air", 0)
    b9 = (state.get("widewash", 0) << 4)
    b11 = (state.get("windspeed", 0) << 4)
    fr = [0xF3, 0xF4, 0, BLE_ADDR, TOILET_ADDR, code, b6, b7, b8, b9, 0, b11, 0, 0, 0, 0, 0]
    fr[2] = len(fr) + 2 - 4
    return finish(fr)


def frame_query():
    fr = [0xF3, 0xF4, 0, BLE_ADDR, 0x00, 0xE2, 0, 0, 0, 0]
    fr[2] = len(fr) + 2 - 4
    return finish(fr)


def on_notify(sender, data):
    b = bytes(data)
    print("收到通知:", hexs(b))
    if len(b) >= 11 and b[0] == 0xF3 and b[1] == 0xF4 and b[5] == 0xE2:
        e, i, s, n = b[6], b[7], b[8], b[9]
        state.update({
            "water": (e >> 4) & 0xF, "autocover": (e >> 3) & 1,
            "gesture": (e >> 2) & 1, "autoflush": (e >> 1) & 1,
            "nightlight": e & 1,
            "hipnozzle": (i >> 4) & 7, "seat": i & 0xF, "savepower": (i >> 7) & 1,
            "smartlight": (s >> 7) & 1, "hippress": (s >> 4) & 7, "air": s & 7,
            "womanpress": (n >> 4) & 7, "womannozzle": n & 7,
            "cover": 0 if (n >> 7) & 1 else 1, "ring": 0 if (n >> 3) & 1 else 1,
        })
        print("解析状态:", {k: v for k, v in state.items()})


async def scan_jomoo(timeout=8.0):
    from bleak import BleakScanner
    results = await BleakScanner.discover(timeout=timeout, return_adv=True)
    named, goodix = [], []
    for addr, (dev, adv) in results.items():
        name = dev.name or getattr(adv, "local_name", None) or ""
        rssi = getattr(adv, "rssi", -999)
        if name.upper().startswith(DEVICE_NAME_PREFIX):
            named.append((dev, rssi, name))
        elif GOODIX_MANUFACTURER_ID in (adv.manufacturer_data or {}):
            goodix.append((dev, rssi, name or "(未见名称)"))
    named.sort(key=lambda x: x[1], reverse=True)
    goodix.sort(key=lambda x: x[1], reverse=True)
    return named, goodix


async def find_toilet(attempts=5, timeout=10.0):
    from bleak import BleakScanner
    known = TOILET_MAC or load_cached_mac()
    if known:
        src = "环境变量 JOMOO_MAC" if TOILET_MAC else f"记录文件 {os.path.basename(MAC_CACHE_FILE)}"
        print(f"使用{src}中的地址: {known}")
        for i in range(2):
            dev = await BleakScanner.find_device_by_address(known, timeout=6.0)
            if dev is not None:
                return dev
            await asyncio.sleep(1.0)
        if TOILET_MAC:
            print("指定的地址没找到设备")
            return None
        print("已记录的设备不在范围内，改为按名称扫描...")
    for i in range(attempts):
        print(f"扫描 {DEVICE_NAME_PREFIX} 设备 ({i + 1}/{attempts})...")
        named, goodix = await scan_jomoo(timeout=timeout)
        if named:
            if len(named) > 1:
                print("发现多台同类设备，选信号最强的：")
                for dev, rssi, name in named:
                    print(f"  {name}  {dev.address}  rssi={rssi}")
            dev, rssi, name = named[0]
            print(f"选中: {name}  {dev.address}  rssi={rssi}")
            if not TOILET_MAC:
                save_cached_mac(dev.address)
                print(f"已记录设备地址到 {MAC_CACHE_FILE}")
            return dev
        if goodix:
            print("没扫描到名称含 JOMOO_SMART 的设备；以下是无名但用 Goodix 芯片的蓝牙设备：")
            for dev, rssi, name in goodix:
                print(f"  {dev.address}  rssi={rssi}  {name}")
            print("将尝试其中信号最强的一台；如果不是马桶请设 JOMOO_MAC 环境变量指定。")
            if not TOILET_MAC:
                save_cached_mac(goodix[0][0].address)
            return goodix[0][0]
        await asyncio.sleep(1.0)
    return None


def b1(on):
    return 1 if on else 0


SIMPLE = {
    ("foot", "on"): lambda: frame_1f(36, 1),
    ("foot", "off"): lambda: frame_1f(36, 2),
    ("uv", "on"): lambda: frame_1f(33, 64),
    ("uv", "off"): lambda: frame_1f(33, 32),
    ("atmo", "on"): lambda: frame_1f(51, 32),
    ("atmo", "off"): lambda: frame_1f(51, 16),
    ("bubble", "on"): lambda: frame_1f(32, 2),
    ("bubble", "off"): lambda: frame_1f(32, 4),
    ("openbubble", "on"): lambda: frame_1f(32, 32),
    ("openbubble", "off"): lambda: frame_1f(32, 64),
    ("bubblerun",): lambda: frame_1f(32, 1),
    ("prewet", "on"): lambda: frame_1f(48, 4),
    ("prewet", "off"): lambda: frame_1f(48, 0),
    ("closeflush", "on"): lambda: frame_1f(37, 1),
    ("closeflush", "off"): lambda: frame_1f(37, 2),
    ("smallflush", "on"): lambda: frame_1f(37, 4),
    ("smallflush", "off"): lambda: frame_1f(37, 8),
    ("closesmallflush", "on"): lambda: frame_1f(37, 16),
    ("closesmallflush", "off"): lambda: frame_1f(37, 32),
    ("filter", "on"): lambda: frame_1f(199, 1),
    ("filter", "off"): lambda: frame_1f(199, 2),
    ("aivoice", "on"): lambda: frame_1f(154, 0),
    ("aivoice", "off"): lambda: frame_1f(155, 0),
    ("petwash", "on"): lambda: frame_1f(63, 8),
    ("petwash", "off"): lambda: frame_1f(63, 4),
    ("selfclean", "on"): lambda: frame_1f(40, 128),
    ("regularselfclean", "on"): lambda: frame_1f(40, 64),
    ("regularselfclean", "off"): lambda: frame_1f(40, 32),
    ("nozzledry", "on"): lambda: frame_1f(53, 16, 0, 0),
    ("autonozzledry", "on"): lambda: frame_1f(53, 8, 0, 0),
    ("autonozzledry", "off"): lambda: frame_1f(53, 4, 0, 0),
    ("liftclean",): lambda: frame_1f(63, 16),
    ("liquidbox",): lambda: frame_1f(32, 16),
    ("forceflush",): lambda: frame_1f(94, 14, 1),
    ("unblock",): lambda: frame_1f(94, 14, 2),
}

SET_KEYS = {
    "autoflush": 1, "autocover": 1, "gesture": 1, "nightlight": 1,
    "smartlight": 1, "savepower": 1,
    "seat": 15, "water": 15, "air": 7, "windspeed": 7,
    "hipnozzle": 7, "hippress": 7, "widewash": 15,
}

ACT_ALIAS = {
    "stop": 0, "autotemp": 2, "dry": 4, "move": 5, "massage": 6,
    "wash-auto-woman": 7, "wash-hip": 8, "nozzle-clean": 9, "defecate": 10,
    "wash-woman": 11, "wash-auto-hip": 12, "bigflush": 14, "flush-big": 14,
    "flush-small": 15, "cover-close": 16, "cover-open": 17, "deodorize": 18,
    "cover-openring": 19, "replace-nozzle": 22, "pos-sync": 24, "sync": 25,
    "sitz": 29,
}


async def send(client, frame, wait=2.5, uuid=None, resp=False):
    print("发送:", hexs(frame))
    await client.write_gatt_char(uuid or WRITE_UUID, frame, response=resp)
    await asyncio.sleep(wait)


async def wait_state(client, timeout=4.0):
    await client.write_gatt_char(WRITE_UUID, frame_query(), response=False)
    for _ in range(int(timeout * 5)):
        if state:
            return True
        await asyncio.sleep(0.2)
    return False


async def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd = argv[0].lower()

    if cmd == "scan":
        if TOILET_MAC:
            print("已用环境变量 JOMOO_MAC 指定地址:", TOILET_MAC)
        cached = load_cached_mac()
        if cached:
            print(f"已记录的地址: {cached}（删除 {os.path.basename(MAC_CACHE_FILE)} 可重新扫描）")
        named, goodix = await scan_jomoo()
        if not named and not goodix:
            print("没找到 JOMOO_SMART（或 Goodix）设备")
            return
        for dev, rssi, name in named:
            print(f"[JOMOO] {name}  {dev.address}  rssi={rssi}")
        for dev, rssi, name in goodix:
            print(f"[Goodix?] {dev.address}  rssi={rssi}  {name}")
        return

    from bleak import BleakClient
    dev = await find_toilet()
    if dev is None:
        print("扫描不到马桶：距离太远或被手机占用。")
        return
    print("找到设备:", dev)

    async with BleakClient(dev, timeout=30.0) as client:
        print("已连接:", client.is_connected)
        for u in NOTIFY_UUIDS:
            try:
                await client.start_notify(u, on_notify)
            except Exception:
                pass

        if cmd == "listen":
            secs = float(argv[1]) if len(argv) > 1 else 10.0
            print(f"监听 {secs:.0f} 秒...")
            await asyncio.sleep(secs)
            return

        if cmd == "query":
            await client.write_gatt_char(WRITE_UUID, frame_query(), response=False)
            await asyncio.sleep(2.5)
            if not state:
                print("未收到状态回复")
            return

        if cmd == "raw":
            args = argv[1:]
            uuid = None
            resp = False
            while args and args[0].lower() in ("ffe1", "f001", "resp", "norsp"):
                a0 = args[0].lower()
                if a0 == "f001":
                    uuid = "0000f001-0000-1000-8000-00805f9b34fb"
                elif a0 == "resp":
                    resp = True
                elif a0 == "norsp":
                    resp = False
                args = args[1:]
            if not args:
                print("用法: raw [resp] [ffe1|f001] F3 F4 06 92 21 1F 24 01 FD FC")
                return
            data = bytes(int(x, 16) for x in args)
            await send(client, data, uuid=uuid, resp=resp)
            return

        arg2 = argv[1].lower() if len(argv) > 1 else ""

        if cmd == "atmo-mode":
            mode = int(argv[1]) if len(argv) > 1 else 0
            await send(client, frame_1f(51, 32 | (mode & 15)))
            return
        if cmd == "dist":
            await send(client, frame_1f(18, int(argv[1]) & 0xFF))
            return
        if cmd == "bright":
            await send(client, frame_1f(42, int(argv[1]) & 0xFF))
            return
        if cmd == "strongdry":
            val = int(argv[1]) if len(argv) > 1 else 0x18
            await send(client, frame_1f(34, val & 0xFF))
            return
        if cmd == "brushtime":
            await send(client, frame_1f(32, 128, int(argv[1]) & 0xFF))
            return
        if cmd == "sens":
            if arg2 == "0":
                await send(client, frame_1f(17, 0))
            else:
                await send(client, frame_1f(16, 0))
            return
        if cmd == "redblue":
            mode = int(argv[1]) if len(argv) > 1 else 0
            red = int(argv[2]) if len(argv) > 2 else 0
            blue = int(argv[3]) if len(argv) > 3 else 0
            await send(client, frame_1f(53, mode, red, blue))
            return

        if cmd == "selfclean" and arg2 == "off":
            cmd = "act"
            argv = ["act", "0"]
        if cmd == "nozzledry" and arg2 == "off":
            cmd = "act"
            argv = ["act", "0"]

        if cmd == "set":
            if len(argv) < 3 or argv[1] not in SET_KEYS:
                print("用法: set <键> <值>，键可选:", " ".join(SET_KEYS))
                return
            key, val = argv[1], argv[2].lower()
            if val in ("on", "1", "open"):
                num = 1
            elif val in ("off", "0", "close"):
                num = 0
            else:
                num = int(val)
            if num > SET_KEYS[key] or num < 0:
                print(f"值范围 0-{SET_KEYS[key]}")
                return
            if not await wait_state(client):
                print("未获取到马桶状态，未发送（防止覆盖其他设置）")
                return
            state[key] = num
            await send(client, frame_19(25))
            return

        if cmd == "act":
            if len(argv) < 2:
                print("用法: act <码或简写>，简写:", " ".join(ACT_ALIAS))
                return
            arg = argv[1].lower()
            code = ACT_ALIAS.get(arg)
            if code is None:
                code = int(arg, 0)
            if not await wait_state(client):
                print("未获取到马桶状态，未发送（动作帧带设置位，防止覆盖设置）")
                return
            await send(client, frame_19(code))
            return

        frame = SIMPLE.get(tuple(a.lower() for a in argv))
        if frame is None:
            print("未知命令，看帮助: python jomoo_toilet.py help")
            return
        await send(client, frame())


if __name__ == "__main__":
    asyncio.run(main())
