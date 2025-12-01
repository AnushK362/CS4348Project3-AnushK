import os
import sys
from typing import List
from __future__ import annotations
from dataclasses import dataclass


magicBytes = b"4348PRJ3"
minimalDegree = 19
maxKeys = 2 * minimalDegree - 1
maxChildren = 2 * minimalDegree
blockSize = 512

def intTo64BitEndianBytes(num: int) -> bytes:
    return num.to_bytes(8, byteorder="big", signed=False)

def bytesTo64Endian(bytes: bytes) -> int:
    if len(bytes) != 8:
        raise ValueError("Expecting exactly 8 bytes")
    return int.from_bytes(bytes, byteorder="big", signed=False)

class header:
    rootBlock: int
    nextBlock: int

    def convertToBytes(self) -> bytes:
    
        blockData = bytearray(blockSize)
        blockData[0:8] = magicBytes
        blockData[8:16] = intTo64BitEndianBytes(self.rootBlock)
        blockData[16:24] = intTo64BitEndianBytes(self.nextBlock)
        return bytes(blockData)
    
    @classmethod
    def convertToNode(conversion, blockData: bytes) -> "header":
        if len(blockData) != blockSize:
            raise ValueError("Header block must be exactly 512 bytes")
        if blockData[0:8] != magicBytes:
            raise ValueError("Not a valid index file")
        rootBlock = bytesTo64Endian(blockData[8:16])
        nextBlock = bytesTo64Endian(blockData[16:24])
        return conversion(rootBlock=rootBlock, nextBlock=nextBlock)
    

class node:
    blockId: int
    numKeys: int
    parentId: int
    vals: List[int]
    keyList: List[int]
    childrenList: List[int]

    def convertToBytes(self) -> bytes:
        offsetVal = 0
        blockData = bytearray(blockSize)
        