import os
dirtools='tools'
tools={}
for root, dirs, files in os.walk(dirtools):
    if root!='__pycache__':
        for file in files:
            if root[6:]==file[:-4] and file.endswith(".exe"):
                path = os.path.join(root, file)
                tools[file[:-4]]='.\\'+path
print(tools)
 