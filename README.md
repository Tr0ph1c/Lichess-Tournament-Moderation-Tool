# arena-check.py
A tool made to help in the moderation / cheat detection on Lichess tournaments. (Arena tournaments) <br>
_NOTE:- The program is in no way intended to replace nor overpower human judgement. It is only intended as a way to speed up the moderation process by highlighting suspicious games / players and providing useful information regarding them as to help the moderator quickly identify any potential cheaters._
__________________
## How to install:
You'll first need some dependencies:
- [Python](https://www.python.org/downloads/)
- A working installation of [Stockfish](https://stockfishchess.org/download/)
- And some Python modules:
-  (chess, stockfish, requests, argparse, time, json)
<br>
** To install any of the previous modules: `pip install <module_name>`.
   
For now, the whole project is only two python files, so just download the repository however you like, and run `arena-check.py`.
__________________
## How to use:
Usage:
```
arena-check.py [-h] [-t THRESHOLD] [-n TOPN] tournament_id

positional arguments:
  tournament_id         The ID of the Lichess arena tournament, the last 8 characters of the tournament's URL.
                        https://lichess.org/tournament/xxxxxxxx

optional arguments:
  -h, --help
                        Show this help message and exit
  -t THRESHOLD, --threshold THRESHOLD
                        The accuracy of play at which to detect a suspicious game. (default: 92)
  -n TOPN, --topn TOPN
                        Number of players from the top to check. (default: 5)
```
_________________
## How it works:
Essentially the program uses [Lichess's API](https://lichess.org/api) to get JSON responses containing the TOP N players and the games they played within the tournament. Then uses a local installation of [Stockfish](https://stockfishchess.org/download/) to evaluate and decide, using a simple accuracy equation, whether the player in this game played suspiciously. It is then up to the user of the program to manually check and ultimately decide whether the suspect was cheating.
<br>
_The linkss for all the analyzed games are outputted by the program for convenience._
