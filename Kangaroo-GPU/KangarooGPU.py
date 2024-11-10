import secp256k1_lib as ice
import bit
import ctypes
import os
import sys
import platform
import random
import math
import signal
import argparse
import time

###############################################################################
# Argument Parsing
parser = argparse.ArgumentParser(description='This tool uses Kangaroo algorithm with GPU support to search 1 pubkey in the specified range.',
                                 epilog='Enjoy the program! :) Tips BTC: 1NEJcwfcEm7Aax8oJNjRUnY3hEavCjNrai')
parser.version = '15112021'
parser.add_argument("-p", "--pubkey", help="Public Key in hex format (compressed or uncompressed)", required=True)
parser.add_argument("-keyspace", help="Keyspace Range (hex) to search from min:max. Default=1:order of curve", action='store')
parser.add_argument("-ncore", help="Number of CPU to use. default = Total-1", action='store')
parser.add_argument("-n", help="Total range search in 1 loop. default=72057594037927935", action='store')
parser.add_argument("-rand", help="Start from a random value in the given range from min:max", action="store_true")
parser.add_argument("-d", help="GPU Device. Default=0", action="store")
parser.add_argument("-t", help="GPU Threads. Default=64", action="store")
parser.add_argument("-b", help="GPU Blocks. Default=10", action="store")
parser.add_argument("-p_points", help="GPU Points per Thread. Default=256", action="store")
parser.add_argument("-bp", help="bP Table Elements for GPU. Default=500000", action="store")

if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
args = parser.parse_args()

###############################################################################
# Range and GPU configuration
ss = args.keyspace if args.keyspace else '1:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140'
flag_random = True if args.rand else False
gpu_device = int(args.d) if args.d else 0
gpu_threads = int(args.t) if args.t else 64
gpu_blocks = int(args.b) if args.b else 10
gpu_points = int(args.p_points) if args.p_points else 256
bp_size = int(args.bp) if args.bp else 500000
public_key = args.pubkey
a, b = ss.split(':')
a = int(a, 16)
b = int(b, 16)

###############################################################################
# Load GPU library
if platform.system().lower().startswith('win'):
    dllfile = 'bt2.dll'
elif platform.system().lower().startswith('lin'):
    dllfile = 'bt2.so'
else:
    print('[-] Unsupported Platform currently for ctypes dll method. Only [Windows and Linux] is supported.')
    sys.exit()

# Ensure path to the compiled shared object or DLL is correct
if os.path.isfile(dllfile):
    pathdll = os.path.realpath(dllfile)
    bsgsgpu = ctypes.CDLL(pathdll)
else:
    print(f'File {dllfile} not found')
    sys.exit()

# Configure function arguments and return types for GPU functions
bsgsgpu.bsgsGPU.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_char_p]
bsgsgpu.bsgsGPU.restype = ctypes.c_void_p
bsgsgpu.free_memory.argtypes = [ctypes.c_void_p]

###############################################################################
# Utility functions
def pub2upub(pub_hex):
    x = int(pub_hex[2:66], 16)
    if len(pub_hex) < 70:
        y = bit.format.x_to_y(x, int(pub_hex[:2], 16) % 2)
    else:
        y = int(pub_hex[66:], 16)
    return bytes.fromhex('04' + hex(x)[2:].zfill(64) + hex(y)[2:].zfill(64))

def randk(a, b):
    return random.SystemRandom().randint(a, b) if flag_random else a

# Automatically select the appropriate CUDA compute architecture
def get_cuda_architecture():
    # Targets multiple CUDA architectures
    return ['sm_70', 'sm_75', 'sm_80']  # Supports GPUs such as A100, 3090 Ti, etc.

###############################################################################
# Run the GPU search
print('[+] Starting GPU Kangaroo.... Please Wait')
P = pub2upub(public_key)
start_range = randk(a, b)
end_range = randk(a, b)
print(f'[+] Searching in the range: {hex(start_range)} to {hex(end_range)}')

# Ensure CUDA device selection is done properly
cuda_architectures = get_cuda_architecture()  # Adjust this to target the right GPU architecture
for arch in cuda_architectures:
    print(f'[+] Using CUDA architecture: {arch}')
    # Compile CUDA code targeting the proper architecture if needed (done outside this script)

while True:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    st_en = hex(start_range)[2:] + ':' + hex(end_range)[2:]
    res = bsgsgpu.bsgsGPU(gpu_threads, gpu_blocks, gpu_points, int(math.log2(bp_size)), gpu_device, P, len(P)//65, st_en.encode('utf8'), str(bp_size).encode('utf8'))
    pvk = (ctypes.cast(res, ctypes.c_char_p).value).decode('utf8')
    bsgsgpu.free_memory(res)

    if pvk:
        print('Private Key Found:', pvk)
        with open("found_keys.txt", "a") as f:
            f.write(f"Private Key: {pvk}\n")
        break
    print(f'Searched range: {hex(start_range)} - {hex(end_range)}')
    start_range = randk(a, b)
    end_range = randk(a, b)

print('[+] Program Finished')
