# MusicBox 0.0.1

## System Requirement

- Node.js® 4.1.2 +
- NPM 1.4.28 +

MusicBox now is support following platform : OSX 10.9+, Ubuntu 14+ and Windows 10.

Besides, MusicBox need port `5566`, make sure that you don't have web server or anything else already run on these port.  

## Setup MusicBox 0.0.1

1) Install dependency of MusicBox packages
```
cd path_of_your_MusicBox_directory
npm install
```
2) Start up the MusicBox

```
cd path_of_your_MusicBox_directory
nodejs Server.js "IoTtalk_ip_address:9999"
```

MusicBox url: http://localhost:5566

MBoxCtl url: http://localhost:5566/mboxctl

## How to connect MusicBox Device Modal with IoTtalk 

1) Create MusicBox and MBoxCtl in your IoTtalk project.

2) Connect all Device Feature 1-1 like this:

![alt text](https://s9.postimg.org/4z32w0uqn/Screen_Shot_2016_09_04_at_8_34_10_PM.png)



## Introduce to MusicBox

The MusicBox IoT application consists of a set of mobile devices who collaborate to play music. The devices can be smart phones or any IoT devices that can play music and/or flush light. There is one conductor who determines which song to play and how to play the song (such as key, mode, period and volume). There is one stage manager who determines the roles of the players and light design. The remaining devices are players responsible for performing the music according to the instructions of the conductor. In terms of the roles of the players, the stage manager first determines the number of players involved, and then groups these players into C clusters. The players in a cluster will have the same behavior.

### Device Feature meaning 
- C: an integer that represents the number of clusters
- N: an integer that represents the number of the players in a cluster
- L: a float number that represents the luminance intensity of the lights
- Song: a JSON-format object representing a MIDI file
- Mode: an integer representing the playing mode. In the sequential mode, the server cuts a song into I P-second segments, and the players sequentially perform the music segment in rotation. For 1<=c<=C and 1<=i <=I, Every player in cluster c performs segment if c= (i mode C). In the parallel mode, the server sends a song to all Players simultaneously then the Players perform the song in parallel.
- Period: an integer P representing the length of a music segment
- Key: an integer representing the altered scale of the played song
- Volume: a float number in decibel (dB), which represents the volume of the played song



