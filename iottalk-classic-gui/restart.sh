#!/bin/sh

venvfile="/home/iottalk/venv/bin/activate"
conffile="/home/iottalk/.iottalk/iottalk.ini"

session_name="iottalk"
retry_time=5
cd $(dirname $0)
guipath=$(pwd)
next_step=false

tmux kill-session -t $session_name 2>/dev/null

for i in $(seq 5)
do
  if [ $(tmux ls 2>/dev/null | grep $session_name | wc -l) -eq "0" ]
  then
    tmux new-session -s $session_name -d;
    next_step=true
    break
  else
    echo "wait previous tmux session kill.....$i"
    sleep 2
  fi
done

if [ "$next_step" != "true" ]
then
    echo "Can't kill previous tmux session..."
else
  sleep 1
  tmux new-window -t iottalk -n csm -d "source $venvfile; iotctl -d -c $conffile start csm; bash -i"
  sleep 0.5
  tmux new-window -t iottalk -n ccm -d "source $venvfile; iotctl -d -c $conffile start ccm; bash -i"

  sleep 0.5
  tmux new-window -t iottalk -n Remote_control -d "source $venvfile; cd $guipath/iotgui/da/Remote_control; python server.py; bash -i"

fi

