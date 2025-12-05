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
    
@dataclass
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
    
    @classmethod
    def bytesToNode(currNode, blockId: int, blockData: bytes) -> "node":
        
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

        return currNode(
            blockId=nodeBlockId,
            parentId=parentId,
            numKeys=numKeys,
            keyList=keyList,
            vals=valueList,
            childrenList=childrenList,
        )

def readBlockatId(n, blockId: int) -> bytes:
    n.seek(blockId * blockSize)
    data = n.read(blockSize)
    if len(data) != blockSize:
        raise IOError("Expected 512 bytes")
    return data


def writeBlockatId(b, blockId: int, blockData: bytes) -> None:
    if len(blockData) != blockSize:
        raise ValueError("Block data must have 512 bytes")
    b.seek(blockId * blockSize)
    b.write(blockData)


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


def splitChild(c, currHeader: header, parent: node, childIndex: int):
    deg = minimalDegree

    aId = parent.childrenList[childIndex]
    a = loadNodeData(c, aId)
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

    saveNodeData(c, a)
    saveNodeData(c, b)

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
            x = x - 1

        currNode.keyList[x+1] = key
        currNode.vals[x+1] = val
        currNode.numKeys += 1
        saveNodeData(n, currNode)
    else:
        while x >= 0 and key < currNode.keyList[x]:
            x = x - 1
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

def genericInsert(n, currHeader: header, currKey: int, val: int):
    found = bTreeSearch(n, currHeader, currKey)
    if found is not None:
        blockId, currNode, idx = found   # unpack 3 values
        currNode.vals[idx] = val
        saveNodeData(n, currNode)
        return

    if currHeader.rootBlock == 0:
        rootId = currHeader.nextBlock
        currHeader.nextBlock += 1
        rootNode = node(
            blockId=rootId,
            parentId=0,
            numKeys=1,
            keyList=[currKey],
            vals=[val],
            childrenList=[0] * maxChildren,
        )
        saveNodeData(n, rootNode)
        currHeader.rootBlock = rootId
        writeHeaderData(n, currHeader)
        return

    rootNode = loadNodeData(n, currHeader.rootBlock)

    if rootNode.numKeys == maxKeys:
        newRootId = currHeader.nextBlock
        currHeader.nextBlock += 1
        newRoot = node(
            blockId=newRootId,
            parentId=0,
            numKeys=0,
            keyList=[],
            vals=[],
            childrenList=[0] * maxChildren,
        )
        newRoot.childrenList[0] = rootNode.blockId
        rootNode.parentId = newRootId
        saveNodeData(n, rootNode)

        splitChild(n, currHeader, newRoot, 0)
        currHeader.rootBlock = newRootId
        saveNodeData(n, newRoot)
        writeHeaderData(n, currHeader)

        insertNonFull(n, currHeader, newRoot, currKey, val)
    else:
        insertNonFull(n, currHeader, rootNode, currKey, val)
        writeHeaderData(n, currHeader)

# Inorder Traversal

def inorderTraverseAction(n, nodeId: int, outputList: List[tuple[int, int]]):
    currNode = loadNodeData(n, nodeId)
    for n in range(currNode.numKeys):
        if currNode.childrenList[n] != 0:
            inorderTraverseAction(n, currNode.childrenList[n], outputList)
        outputList.append((currNode.keyList[n], currNode.vals[n]))
    if currNode.childrenList[currNode.numKeys] != 0:
        inorderTraverseAction(n, currNode.childrenList[currNode.numKeys], outputList)

def cmdCreateFile(fileName: str) -> None:
    if os.path.exists(fileName):
        print("The file already exists", file=sys.stderr)
        sys.exit(1)

    setHeader = header(rootBlock=0, nextBlock=1) 

    with open(fileName, "wb") as f:
        writeHeaderData(f, setHeader)

    print(f"Created a new index file'{fileName}'")

def updateIndexFile(filePath: str):
    if not os.path.exists(filePath):
        print("The index file does not exist", file=sys.stderr)
        sys.exit(1)
    currFile = open(filePath, "r+b")
    try:
        currHeader = readHeaderData(currFile)
    except Exception as e:
        currFile.close()
        print("The file is invalid", e, file=sys.stderr)
        sys.exit(1)
    return currFile, currHeader

def insertOperation(filePath: str, currKey: str, currVal: str) -> None:
    try:
        realKey = int(currKey)
        realVal = int(currVal)
    except ValueError:
        print("Please enter integers on the command line", file=sys.stderr)
        sys.exit(1)

    node, currHeader = updateIndexFile(filePath)
    with node:
        genericInsert(node, currHeader, realKey, realVal)

def searchOperation(filePath: str, searchKey: str) -> None:
    try:
        currKey = int(searchKey)
    except ValueError:
        print("Key must be integer", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(filePath):
        print("The index file does not exist", file=sys.stderr)
        sys.exit(1)

    with open(filePath, "rb") as file:
        try:
            currHeader = readHeaderData(file)
        except Exception as exc:
            print("The index file is in invalid", exc, file=sys.stderr)
            sys.exit(1)

        searchResult = bTreeSearch(file, currHeader, currKey)
        if searchResult is None:
            print("Node not found")
        else:
            blockId, currNode, idx = searchResult
            print(f"{currNode.keyList[idx]} {currNode.vals[idx]}")

def loadOperation(filePath: str, csvPath: str) -> None:
    if not os.path.exists(csvPath):
        print("CSV file does not exist", file=sys.stderr)
        sys.exit(1)

    f, currHeader = updateIndexFile(filePath)
    
    with f, open(csvPath, "r", encoding="utf-8") as currFile:
        for currLine in currFile:
            currLine = currLine.strip()
            if not currLine:
                continue
            components = currLine.split(",")
            if len(components) != 2:
                print("Skipping improper line:", currLine, file=sys.stderr)
                continue
            searchKey, searchValue = components
            try:
                stripKey = int(searchKey.strip())
                rawValue = int(searchValue.strip())
            except ValueError:
                print("Skipping non-integer line", currLine, file=sys.stderr)
                continue
            genericInsert(f, currHeader, stripKey, rawValue)

def printOperation(filePath: str) -> None:
    if not os.path.exists(filePath):
        print("The index file does not exist", file=sys.stderr)
        sys.exit(1)

    with open(filePath, "rb") as file:
        try:
            currHeader = readHeaderData(file)
        except Exception as exc:
            print("The index file is invalid", exc, file=sys.stderr)
            sys.exit(1)

        if currHeader.rootBlock == 0:
            return

        pairings: List[tuple[int, int]] = []
        inorderTraverseAction(file, currHeader.rootBlock, pairings)
        for key, val in pairings:
            print(f"{key} {val}")

def extractOperation(filePath: str, outputPath: str) -> None:
    if os.path.exists(outputPath):
        print("The Output file already exists", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(filePath):
        print("The Index file does not exist", file=sys.stderr)
        sys.exit(1)

    with open(filePath, "rb") as newFile:
        try:
            currHeader = readHeaderData(newFile)
        except Exception as exc:
            print("Invalid index file:", exc, file=sys.stderr)
            sys.exit(1)

        with open(outputPath, "w", encoding="utf-8") as outputFile:
            if currHeader.rootBlock == 0:
                return

            pairings: List[tuple[int, int]] = []
            inorderTraverseAction(newFile, currHeader.rootBlock, pairings)
            for key, val in pairings:
                outputFile.write(f"{key},{val}\n")



def main(argList: List[str]) -> None:
    if len(argList) < 2:
        print("usage: project3.py <command> [args...]", file=sys.stderr)
        sys.exit(1)

    currCommand = argList[1]

    if currCommand == "create":
        if len(argList) != 3:
            print("Usage: project3.py create <indexfile>", file=sys.stderr)
            sys.exit(1)
        cmdCreateFile(argList[2])
    elif currCommand == "insert":
        if len(argList) != 5:
            print("Usage: project3.py insert <indexfile> <key> <value>", file=sys.stderr)
            sys.exit(1)
        insertOperation(argList[2], argList[3], argList[4])
    elif currCommand == "load":
        if len(argList) != 4:
            print("Usage: project3.py load <indexfile> <csvfile>", file=sys.stderr)
            sys.exit(1)
        loadOperation(argList[2], argList[3])
    elif currCommand == "search":
        if len(argList) != 4:
            print("Usage: project3.py search <indexfile> <key>", file=sys.stderr)
            sys.exit(1)
        searchOperation(argList[2], argList[3])
    elif currCommand == "extract":
        if len(argList) != 4:
            print("Usage: project3.py extract <indexfile> <csvfile>", file=sys.stderr)
            sys.exit(1)
        extractOperation(argList[2], argList[3])
    elif currCommand == "print":
        if len(argList) != 3:
            print("Usage: project3.py print <indexfile>", file=sys.stderr)
            sys.exit(1)
        printOperation(argList[2])


if __name__ == "__main__":
    main(sys.argv)