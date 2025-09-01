#!/usr/bin/python
# This is pydp100 file
# author: zhj@ihep.ac.cn
# 2024-01-19 created

import crcmod
import hid
import time

VID = 0x2E3C
PID = 0xAF01

DR_H2D = 0xFB
DR_D2H = 0xFA

OP_NONE = 0x00
OP_DEVICEINFO = 0x10
OP_BASICINFO = 0x30
OP_BASICSET = 0x35
OP_SYSTEMINFO = 0x40
OP_SCANOUT = 0x50
OP_SERIALOUT = 0x55

vin = 0  # unit: mV
vout = 0  # unit: mV
iout = 0  # unit: mA
vo_max = 0  # unit: mV
temp1 = 0  # unit: 0.1 degC
temp2 = 0  # unit: 0.1 degC
dc_5v = 0  # unit: mV
out_mode = 0
work_st = 0

dev_type = ""
hdw_ver = 0
app_ver = 0
boot_ver = 0
run_area = 0
dev_sn = bytes([])
year = 0
month = 0
day = 0

blk_lev = 0
opp = 0  # unit: mV
otp = 0  # unit: 0.1 degC
vol_lev = 0

index = 0
state = 0  # 0:off; 1:on
vo_set = 0  # unit: mV
io_set = 0  # unit: mA
ovp_set = 0  # unit: mV
ocp_set = 0  # unit: mA

SET_MODIFY = 0x20
SET_ACT = 0x80

crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)


def gen_frame(op_code, data=bytes([])):
    frame = bytes([DR_H2D, op_code & 0xFF, 0x0, len(data) & 0xFF]) + data
    crc = crc16(frame)
    return frame + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def check_frame(data):
    global vin, vout, iout, vo_max, temp1, temp2, dc_5v, out_mode, work_st
    global dev_type, hdw_ver, app_ver, boot_ver, run_area, dev_sn, year, month, day
    global blk_lev, opp, otp, vol_lev
    global index, state, vo_set, io_set, ovp_set, ocp_set

    if data[0] == DR_D2H:
        op = data[1]
        data_len = data[3]
        if crc16(data[0 : 4 + data_len + 2]) == 0:  # correct if return 0
            raw_data = data[4 : 4 + data_len]
            # print(raw_data)
            if op == OP_BASICINFO:
                vin = (raw_data[1] << 8) | raw_data[0]
                vout = (raw_data[3] << 8) | raw_data[2]
                iout = (raw_data[5] << 8) | raw_data[4]
                vo_max = (raw_data[7] << 8) | raw_data[6]
                temp1 = (raw_data[9] << 8) | raw_data[8]
                temp2 = (raw_data[11] << 8) | raw_data[10]
                dc_5v = (raw_data[13] << 8) | raw_data[12]
                out_mode = raw_data[14]
                work_st = raw_data[15]
                # print(vin,vout,iout,vo_max,temp1,temp2,dc_5v,out_mode,work_st)
            elif op == OP_DEVICEINFO:
                dev_type = raw_data[0:15].split(b"\x00")[0].decode("utf-8")
                hdw_ver = (raw_data[17] << 8) | raw_data[16]  # origin:11 means 1.1
                app_ver = (raw_data[19] << 8) | raw_data[18]  # origin:11 means 1.1
                boot_ver = (raw_data[21] << 8) | raw_data[20]
                run_area = (raw_data[23] << 8) | raw_data[22]
                dev_sn = raw_data[24 : 24 + 11]
                year = (raw_data[37] << 8) | raw_data[36]
                month = raw_data[38]
                day = raw_data[39]
                # print(dev_type,hdw_ver,app_ver,boot_ver,run_area,dev_sn,year,month,day)
            elif op == OP_SYSTEMINFO:
                blk_lev = raw_data[0]  # backlight
                opp = (raw_data[2] << 8) | raw_data[1]  # over power
                otp = (raw_data[4] << 8) | raw_data[3]  # over temperature
                vol_lev = raw_data[5]  # beep volumn
                # print(blk_lev, opp, otp, vol_lev)
            elif op == OP_BASICSET:
                if data_len == 1:
                    assert raw_data[0] == 1
                    return
                index = raw_data[0]
                state = raw_data[1]
                vo_set = (raw_data[3] << 8) | raw_data[2]
                io_set = (raw_data[5] << 8) | raw_data[4]
                ovp_set = (raw_data[7] << 8) | raw_data[6]
                ocp_set = (raw_data[9] << 8) | raw_data[8]
                # print(index, state, vo_set, io_set, ovp_set, ocp_set)
        else:
            print("CRC ERROR")


def gen_set(output=False, vset=0, iset=0, ovp=30500, ocp=5050):
    return bytes(
        [
            SET_MODIFY,
            1 if output else 0,
            vset & 0xFF,
            (vset >> 8) & 0xFF,
            iset & 0xFF,
            (iset >> 8) & 0xFF,
            ovp & 0xFF,
            (ovp >> 8) & 0xFF,
            ocp & 0xFF,
            (ocp >> 8) & 0xFF,
        ]
    )


with hid.Device(VID, PID) as dp100:
    print(f"Device manufacturer: {dp100.manufacturer}, Serial number: {dp100.serial}")

    dp100.write(gen_frame(OP_DEVICEINFO))
    time.sleep(0.05)
    check_frame(dp100.read(64))
    print(
        f"{dev_type} hardware {hdw_ver/10}, app {app_ver/10}, bootloader {boot_ver/10} @ {year}-{month}-{day}"
    )

    dp100.write(gen_frame(OP_BASICINFO))
    time.sleep(0.05)
    check_frame(dp100.read(64))
    print(f"Vi: {vin/1000}V, Vo: {vout/1000}V, Io: {iout/1000}A, temp: {temp1/10}degC")

    dp100.write(gen_frame(OP_BASICSET, bytes([SET_ACT])))
    time.sleep(0.05)
    check_frame(dp100.read(64))
    print(
        f"state:{state}, Vo_set:{vo_set/1000}V, Io_set{io_set/1000}A, OVP:{ovp_set/1000}V, OCP:{ocp_set/1000}A"
    )

    dp100.write(
        gen_frame(OP_BASICSET, gen_set(False, vo_set, io_set, ovp_set, ocp_set))
    )
    time.sleep(0.05)
    check_frame(dp100.read(64))
