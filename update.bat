@echo off

echo �ύ��ǰ�Ķ�...
git add .
git commit -m 'timely-commit'

echo �������´��벢���Ǳ���...
git fetch --depth=1
git reset --hard origin/master
git pull

echo ���������ɣ�
pause