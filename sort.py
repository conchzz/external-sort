import heapq
import os
import struct
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor


SZ = 4
FM = "<i"
MAX_F = 128


def chk():
    if len(sys.argv) != 3:
        raise SystemExit("error")

    in_f = os.path.abspath(sys.argv[1])

    try:
        max_n = int(sys.argv[2])
    except ValueError:
        raise SystemExit("error")

    wk = os.cpu_count() or 1

    if max_n < max(2, wk):
        raise SystemExit("error")

    if not os.path.isfile(in_f):
        raise SystemExit("error")

    if os.path.getsize(in_f) % SZ != 0:
        raise SystemExit("error")

    return in_f, max_n, wk


def out_nm(in_f):
    p = os.path.dirname(in_f)
    f = os.path.basename(in_f)
    nm, ext = os.path.splitext(f)
    return os.path.join(p, nm + "_sorted" + ext)


def rd(f, cnt):
    data = f.read(cnt * SZ)
    nums = []

    for x in struct.iter_unpack(FM, data):
        nums.append(x[0])

    return nums


def wr(f, nums):
    for x in nums:
        f.write(struct.pack(FM, x))


def rd1(f):
    data = f.read(SZ)

    if data == b"":
        return None

    return struct.unpack(FM, data)[0]


def sort_part(t):
    in_f, st, cnt, tmp, num = t

    with open(in_f, "rb") as f:
        f.seek(st * SZ)
        nums = rd(f, cnt)

    nums.sort()

    tmp_f = os.path.join(tmp, "part_" + str(num) + ".bin")

    with open(tmp_f, "wb") as f:
        wr(f, nums)

    return tmp_f


def mk_tasks(in_f, max_n, tmp, wk):
    all_n = os.path.getsize(in_f) // SZ
    part_sz = max_n // wk

    tasks = []
    num = 0

    for st in range(0, all_n, part_sz):
        cnt = min(part_sz, all_n - st)
        tasks.append((in_f, st, cnt, tmp, num))
        num += 1

    return tasks


def mrg_group(files, out_f):
    fs = []
    h = []

    try:
        for i, name in enumerate(files):
            f = open(name, "rb")
            fs.append(f)

            x = rd1(f)
            if x is not None:
                heapq.heappush(h, (x, i))

        with open(out_f, "wb") as out:
            while h:
                x, i = heapq.heappop(h)
                out.write(struct.pack(FM, x))

                nxt = rd1(fs[i])
                if nxt is not None:
                    heapq.heappush(h, (nxt, i))

    finally:
        for f in fs:
            f.close()


def mrg(parts, out_f, tmp, max_n):
    if len(parts) == 0:
        open(out_f, "wb").close()
        return

    width = min(max_n, MAX_F)
    round_n = 0

    while len(parts) > 1:
        new_parts = []
        group_n = 0

        for i in range(0, len(parts), width):
            group = parts[i:i + width]

            if len(group) == 1:
                new_parts.append(group[0])
                continue

            tmp_f = os.path.join(tmp, "mrg_" + str(round_n) + "_" + str(group_n) + ".bin")

            mrg_group(group, tmp_f)
            new_parts.append(tmp_f)

            for name in group:
                os.remove(name)

            group_n += 1

        parts = new_parts
        round_n += 1

    os.replace(parts[0], out_f)


if __name__ == "__main__":
    in_f, max_n, wk = chk()

    out_f = out_nm(in_f)
    folder = os.path.dirname(in_f)

    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        tasks = mk_tasks(in_f, max_n, tmp, wk)

        with ProcessPoolExecutor(max_workers=wk) as pool:
            parts = list(pool.map(sort_part, tasks))

        mrg(parts, out_f, tmp, max_n)

    print("result file:", out_f)