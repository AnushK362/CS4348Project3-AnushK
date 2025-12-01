from __future__ import annotations
import os
import sys
from typing import List
from dataclasses import dataclass


magicBytes = b"4348PRJ3"
minimalDegree = 10
maxKeys = 2 * minimalDegree - 1
maxChildren = 2 * minimalDegree
blockSize = 512

def intTo64BitEndianBytes(num: int) -> bytes:
    return num.to_bytes(8, byteorder="big", signed=False)

def bytesTo64Endian(currBytes: bytes) -> int:
    if len(currBytes) != 8:
        raise ValueError("Expecting exactly 8 bytes")
    return int.from_bytes(currBytes, byteorder="big", signed=False)

@dataclass
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
    def convertToHeader(conversion, blockData: bytes) -> "header":
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

        blockData[offsetVal:offsetVal+8] = intTo64BitEndianBytes(self.blockId)
        offsetVal += 8
        blockData[offsetVal:offsetVal+8] = intTo64BitEndianBytes(self.parentId)
        offsetVal += 8
        blockData[offsetVal:offsetVal+8] = intTo64BitEndianBytes(self.numKeys)
        offsetVal += 8
        
        for k in range(maxKeys):
            currVal = self.keyList[k] if k < len(self.keyList) else 0
            blockData[offsetVal:offsetVal+8] = intTo64BitEndianBytes(currVal)
            offsetVal += 8

        for k in range(maxKeys):
            currVal = self.vals[k] if k < len(self.vals) else 0
            blockData[offsetVal:offsetVal+8] = intTo64BitEndianBytes(currVal)
            offsetVal += 8

        for k in range(maxChildren):
            currChild = self.childrenList[k] if k < len(self.childrenList) else 0
            blockData[offsetVal:offsetVal+8] = intTo64BitEndianBytes(currChild)
            offsetVal += 8

        return bytes(blockData)
    
    def bytesToNode(currInst, blockId: int, blockData: bytes) -> "node":
        
        if len(blockData) != blockSize:
            raise ValueError("Node block must be 512 bytes")
        
        offset = 0

        nodeBlockId = bytesTo64Endian(blockData[offset:offset+8]); offset += 8
        parentId = bytesTo64Endian(blockData[offset:offset+8]); offset += 8
        numKeys = bytesTo64Endian(blockData[offset:offset+8]); offset += 8

        if nodeBlockId != blockId:
            raise ValueError("Node block ID mismatch")
        
        keyList = []
        for _ in range(maxKeys):
            keyList.append(bytesTo64Endian(blockData[offset:offset+8]))
            offset += 8

        valueList = []
        for _ in range(maxKeys):
            valueList.append(bytesTo64Endian(blockData[offset:offset+8]))
            offset += 8

        childrenList = []
        for _ in range(maxChildren):
            childrenList.append(bytesTo64Endian(blockData[offset:offset+8]))
            offset += 8

        keyList = keyList[:numKeys] #filter and match with keys
        valueList = valueList[:numKeys]

        return currInst(
            blockId=nodeBlockId,
            parentId=parentId,
            numKeys=numKeys,
            keyList=keyList,
            vals=valueList,
            childrenList=childrenList,
        )

def readBlockatId(n, block_id: int) -> bytes:
    n.seek(block_id * blockSize)
    data = n.read(blockSize)
    if len(data) != blockSize:
        raise IOError("Expected 512 bytes")
    return data


def writeBlockatId(b, block_id: int, block_data: bytes) -> None:
    if len(block_data) != blockSize:
        raise ValueError("Block data must have 512 bytes")
    b.seek(block_id * blockSize)
    b.write(block_data)


def readHeaderData(x) -> header:
    blockData = readBlockatId(x, 0)
    return header.convertToHeader(blockData)


def writeHeaderData(a, header: header) -> None:
    writeBlockatId(a, 0, header.convertToBytes())


def loadNodeData(l, blockId: int) -> node:
    blockData = readBlockatId(l, blockId)
    return node.bytesToNode(blockId, blockData)


def saveNodeData(p, currNode: node) -> None:
    blockData = currNode.convertToBytes()
    writeBlockatId(p, currNode.blockId, blockData)

def isLeaf(currNode: node) -> bool:
    return all(curr == 0 for curr in currNode.childrenList[:currNode.numKeys+1])

def bTreeSearch(b, currHeader: header, givenKey: int):
    if currHeader.rootBlock == 0:
        return None

    currId = currHeader.rootBlock
    while True:
        currNode = loadNodeData(b, currId)

        temp = 0
        while temp < currNode.numKeys and givenKey > currNode.keyList[temp]:
            temp += 1

        if temp < currNode.numKeys and givenKey == currNode.keyList[temp]:
            return (currId, currNode, temp)

        if isLeaf(currNode):
            return None

        childId = currNode.childrenList[temp]
        if childId == 0:
            return None
        currId = childId


def splitChild(f, currHeader: header, parent: node, childIndex: int):
    deg = minimalDegree

    aId = parent.childrenList[childIndex]
    a = loadNodeData(f, aId)
    if a.numKeys != maxKeys:
        raise ValueError("split cannot happen here")

    bId = currHeader.nextBlock
    currHeader.nextBlock += 1

    midKey = a.keyList[deg-1]
    midVal = a.vals[deg-1]

    bKeys = a.keyList[deg:]
    bVals = a.vals[deg:]

    bChildren = [0] * maxChildren
    if not isLeaf(a):
        for d in range(deg):
            bChildren[d] = a.childrenList[deg + d]
            a.childrenList[deg + d] = 0

    b = node(
        blockId= bId,
        parentId= parent.blockId,
        numKeys= deg-1,
        keyList= bKeys,
        vals= bVals,
        childrenList= bChildren,
    )

    a.keyList = a.keyList[:deg-1]
    a.vals = a.vals[:deg-1]
    a.numKeys = deg-1

    saveNodeData(f, a)
    saveNodeData(f, b)

    parent.childrenList.insert(childIndex + 1, bId)
    parent.childrenList = parent.childrenList[:maxChildren]

    parent.keyList.insert(childIndex, midKey)
    parent.vals.insert(childIndex, midVal)
    parent.numKeys += 1


def insertNonFull(n, currHeader: header, currNode: node, key: int, val: int):
    x = currNode.numKeys - 1

    if isLeaf(currNode):
        currNode.keyList.append(0)
        currNode.vals.append(0)

        while x >= 0 and key < currNode.keyList[x]:
            currNode.keyList[x+1] = currNode.keyList[x]
            currNode.vals[x+1] = currNode.vals[x]
            x -= 1

        currNode.keyList[x+1] = key
        currNode.vals[x+1] = val
        currNode.numKeys += 1
        saveNodeData(n, currNode)
    else:
        while x >= 0 and key < currNode.keyList[x]:
            x -= 1
        x += 1
        childId = currNode.childrenList[x]
        child = loadNodeData(n, childId)

        if child.numKeys == maxKeys:
            splitChild(n, currHeader, node, x)
            saveNodeData(n, node)
            writeHeaderData(n, currHeader)
            if key > currNode.keyList[x]:
                x += 1
            childId = currNode.childrenList[x]
            child = loadNodeData(n, childId)

        insertNonFull(n, currHeader, child, key, val)

def cmdCreateFile(path: str) -> None:
    if os.path.exists(path):
        print("error: File already exists", file=sys.stderr)
        sys.exit(1)

    setHeader = header(rootBlock=0, nextBlock=1) 

    with open(path, "wb") as f:
        writeHeaderData(f, setHeader)

    print(f"Created index file '{path}'")

def main(argList: List[str]) -> None:
    if len(argList) < 2:
        print("usage: project3.py <command> [args...]", file=sys.stderr)
        sys.exit(1)

    currCommand = argList[1]

    if currCommand == "create":
        if len(argList) != 3:
            print("usage: project3.py create <indexfile>", file=sys.stderr)
            sys.exit(1)
        cmdCreateFile(argList[2])
    else:
        print(f"error: command '{currCommand}' not implemented yet", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)