def binvec2dec(binvec):
    return sum([binvec[i]*(2**i) for i in range(0,len(binvec))])

def ismember(list1, list2):
    return [any([kb == kp for kp in list2]) for kb in list1]