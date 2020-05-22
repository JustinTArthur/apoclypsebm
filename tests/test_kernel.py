import os
import pkgutil
from binascii import unhexlify
from struct import unpack

import pyopencl as cl

from apoclypsebm.sha256 import partial, calculateF, sha256, STATE
from apoclypsebm.util import uint32, uint32_as_bytes

DEFAULT_FRAMES = 30


def file_safe_sanitize(name):
    return name.replace(':', '-')


def try_kernel(platform_idx, device_idx):
    platforms = cl.get_platforms()
    device = platforms[platform_idx].get_devices()[device_idx]
    worksize = device.get_info(cl.device_info.MAX_WORK_GROUP_SIZE)
    context = cl.Context([device], None, None)
    output_size = 256
    host_out_buffer = bytearray((output_size + 1) * 4)
    cl_out_buffer = cl.Buffer(
        context,
        cl.mem_flags.WRITE_ONLY,
        size=len(host_out_buffer)
        # hostbuf=host_out_buffer
    )

    defines = (
          f'-D OUTPUT_SIZE={output_size} -D OUTPUT_MASK={output_size - 1} '
          f'-D WORK_GROUP_SIZE={worksize}'
    )
    if device.extensions.find('cl_amd_media_ops') != -1:
        print('AMD bitalign defined!')
        defines += ' -DBITALIGN'

    kernel_code = pkgutil.get_data('apoclypsebm', 'apoclypse-0.cl').decode('ascii')
    print(f'Building with {defines}')
    program = cl.Program(context, kernel_code).build(defines)

    kernel_bin_file_name = file_safe_sanitize(
        f'{device.platform.name}-{device.platform.version}-{device.name}.elf'
    )
    with open(kernel_bin_file_name, 'wb') as binary:
        binary.write(program.binaries[0])
    print(f'Wrote kernel to {kernel_bin_file_name}')

    kernel = program.search

    frame = 1.0 / DEFAULT_FRAMES
    unit = worksize * 256
    global_threads = unit * 10

    print(f'worksize: {worksize},  unit: {unit},  global_threads: {global_threads}')

    kernel.set_arg(20, cl_out_buffer)

    base = 0

    work = None  # TODO
    rate_divisor, hashspace = 1000, 0xFFFFFFFF  # assumes not vectorized
    nonces_left = hashspace

    with open('../example_blochheader_block.txt') as block_file:
        binary_data = unhexlify(block_file.read())[:76]
        # Swap every uint32 for sha256…
    swapped_bin = bytearray()
    for i in range(-1, len(binary_data) - 1, 4):
        new_word = binary_data[i+4:None if i==-1 else i:-1]
        swapped_bin += new_word
        # print(f'slicing {i + 3}:{i or None}:{-1} gives {new_word.hex()}')
    print(f'Initial: {binary_data.hex()}')
    print(f'SHA2 chunked: {swapped_bin.hex()}')

    midstate_input = list(unpack('<16I', swapped_bin[:64])) + ([0] * 48)
    midstate = sha256(STATE, midstate_input)
    merkle_end = uint32(unpack('<I', swapped_bin[64:68])[0])
    time = uint32(unpack('<I', swapped_bin[68:72])[0])
    difficulty = uint32(unpack('<I', swapped_bin[72:76])[0])

    base = 316141196 - 0  # -10 from the winner

    print(f'')


    state = list(midstate)
    f = [0] * 8
    state2 = partial(state, merkle_end, time, difficulty, f)
    print(f'state2 and f: {state2}, {f}')
    calculateF(state, merkle_end, time, difficulty, f, state2)
    print(f'state and f after fcalc: {state}, {f}')
    kernel.set_arg(0, uint32_as_bytes(state[0]))
    kernel.set_arg(1, uint32_as_bytes(state[1]))
    kernel.set_arg(2, uint32_as_bytes(state[2]))
    kernel.set_arg(3, uint32_as_bytes(state[3]))
    kernel.set_arg(4, uint32_as_bytes(state[4]))
    kernel.set_arg(5, uint32_as_bytes(state[5]))
    kernel.set_arg(6, uint32_as_bytes(state[6]))
    kernel.set_arg(7, uint32_as_bytes(state[7]))

    kernel.set_arg(8, uint32_as_bytes(state2[1]))
    kernel.set_arg(9, uint32_as_bytes(state2[2]))
    kernel.set_arg(10, uint32_as_bytes(state2[3]))
    kernel.set_arg(11, uint32_as_bytes(state2[5]))
    kernel.set_arg(12, uint32_as_bytes(state2[6]))
    kernel.set_arg(13, uint32_as_bytes(state2[7]))

    kernel.set_arg(15, uint32_as_bytes(f[0]))
    kernel.set_arg(16, uint32_as_bytes(f[1]))
    kernel.set_arg(17, uint32_as_bytes(f[2]))
    kernel.set_arg(18, uint32_as_bytes(f[3]))
    kernel.set_arg(19, uint32_as_bytes(f[4]))

    # This part usually done after temperature check:
    print(f'Starting with base {base}')
    kernel.set_arg(14, uint32_as_bytes(base)[::-1])
    cmd_queue = cl.CommandQueue(context)
    cl.enqueue_copy(cmd_queue, cl_out_buffer, host_out_buffer)
    cl.enqueue_nd_range_kernel(cmd_queue, kernel,
                               (global_threads,), (worksize,))

    cl.enqueue_copy(cmd_queue, host_out_buffer, cl_out_buffer)
    cmd_queue.finish()
    print(f'Got {len(host_out_buffer)} outputs:')
    print(' '.join([f'{nonce:02x}' for nonce in host_out_buffer]))

    nonces_left -= global_threads
    # threads_run_pace += global_threads
    # threads_run += global_threads
    base = uint32(base + global_threads)


if __name__ == '__main__':
    # os.environ['PYOPENCL_']
    try_kernel(0, 2)
