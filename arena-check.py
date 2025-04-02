import requests
import argparse
import time
import json

import analysis

# ================= #
#     Constants     #
# ================= #

LICHESS_API_BASE_URL = "https://lichess.org/api"
HEADERS = {"User-Agent": "lichess-arena-moderation-tool-v1.0"}
API_DELAY_SECONDS = 2
REQUEST_TIMEOUT = 30

# ===================== #
#    Helper Functions   #
# ===================== #

# Makes a GET request to the Lichess API and handles basic errors.
def LichessAPICall(endpoint, params=None, stream=False, accept="application/json"):
    # Try 3 times then quit
    for _ in range(3):
        url = f"{LICHESS_API_BASE_URL}/{endpoint}"
        try:
            headers = HEADERS.copy()
            headers["Accept"] = accept
            response = requests.get(url, params=params, headers=headers, stream=stream, timeout=REQUEST_TIMEOUT)

            # "If you receive an HTTP response with a 429 status, please wait a full minute before resuming API usage..."
            #     ~ https://lichess.org/api#section/Introduction/Rate-limiting
            if response.status_code == 429:
                print("** WARNING: Rate limited by Lichess API. Consider increasing API_DELAY_SECONDS.")
                print("      Waiting 1 minute as specified by the lichess api usage instructions...")
                print("      Consider raising the API_DELAY_SECONDS of the script.")
                time.sleep(60 + API_DELAY_SECONDS) # Safety margin
                print("\nRetrying the API call.")
                continue

            response.raise_for_status() # Raise HTTPError if failed.

            return response
        except requests.exceptions.HTTPError as e:
            print(f"ERROR: API request failed for endpoint '{endpoint}'. Error: {e}")
            print(f"Waiting {API_DELAY_SECONDS}s and trying again...")
            time.sleep(API_DELAY_SECONDS)
            continue
        except requests.exceptions.ReadTimeout as e:
            print(f"ERROR: API request timed out.")
            print(f"Waiting {API_DELAY_SECONDS}s and trying again...")
            time.sleep(API_DELAY_SECONDS)
            continue
        except Exception as e:
            print(f"Unexpected error while sending HTTP request: {e}")
            print(f"Waiting {API_DELAY_SECONDS}s and trying again...")
            time.sleep(API_DELAY_SECONDS)
            continue
    # End trying the request
    print("-" * 20)
    print("API request failed too many times, quitting.")
    print("-" * 20)
    raise SystemExit

# Parses ndjson from a response.
def ParseNDJSON(response: requests.Response):
    data = []
    
    try:
        for line in response.iter_lines():
            if line:
                try:
                    data.append(json.loads(line.decode('utf-8')))
                except json.JSONDecodeError as e:
                    print(f"WARN: Could not decode JSON line: {line.decode('utf-8')}. Error: {e}")
                    continue
    except requests.exceptions.ChunkedEncodingError as e:
        print(f"WARN: Error reading stream response: {e}")
    finally:
        response.close() # Ensure the connection is closed

    return data


# ===================== #
#     Main Functions    #
# ===================== #

# Fetches the usernames of the top N players from tournament results.
def GetTopPlayers(tournament_id, num_players):
    print(f"Fetching top {num_players} players for tournament {tournament_id}...")
    # "Players of an Arena tournament, with their score and performance, sorted by rank (best first). Players are streamed as ndjson"
    #    ~ https://lichess.org/api#tag/Arena-tournaments/operation/resultsByTournament
    #
    # 'nb' parameter used to limit the number of players returned directly.
    response = LichessAPICall(f"tournament/{tournament_id}/results", params={'nb': num_players}, stream=True, accept="application/x-ndjson")
    players = []
    if response:
        results = ParseNDJSON(response)
        for player_data in results:
            username = player_data.get('username')

            if username:
                players.append(username)
            else:
                print(f"WARNING: Could not find username in player data: {player_data}")

        return players
    else:
        return []

# Fetches player's games within the tournament timeframe, requesting analysis.
def GetPlayerGamesInTournament(username, tournament_id):
    print(f"\nChecking games for player: {username}")

    params = {
        'player'    : username,
        'moves'     : True,     # Will use PGN to do local analysis.
    }

    response = LichessAPICall(f"tournament/{tournament_id}/games", params=params, stream=True, accept="application/x-ndjson")
    games = []
    if response:
        games = ParseNDJSON(response)
    return games

# Checks if the specified player's accuracy in the game exceeds the threshold.
# Returns (True, analysis, color) if exceeded, (False, analysis, color) otherwise.
def CheckGameAccuracy(game, player_username, accuracy_threshold):
    game_id = game.get('id', 'N/A')
    game_moves = game.get('moves', 'N/A')
    players = game.get('players')

    player_lower = player_username.lower()
    player_color = None

    # Determine player color and get corresponding analysis object
    white_player = players.get('white', {}).get('user', {}).get('name', '').lower()
    black_player = players.get('black', {}).get('user', {}).get('name', '').lower()

    if white_player == player_lower:
        player_color = "(White)"
        analysis_results = analysis.AnalyzeGame(game_moves, True)
    elif black_player == player_lower:
        player_color = "(Black)"
        analysis_results = analysis.AnalyzeGame(game_moves, False)
    else:
        print(f"WARNING: Player {player_username} not found in game {game_id} players: {players}")
        return False, analysis_results, player_color

    if analysis_results['accuracy'] >= accuracy_threshold:
        return True, analysis_results, player_color
    else:
        return False, analysis_results, player_color


# ==================== #
#     Access Point     #
# ==================== #

def main():
    parser = argparse.ArgumentParser(description="Tool to check accuracies of top arena tournament standings in lichess.")
    parser.add_argument("tournament_id", help="The ID of the Lichess arena tournament, the last 8 characters of the tournament's URL. https://lichess.org/tournament/xxxxxxxx")
    parser.add_argument("-t", "--threshold", type=float, default=95.0, help="The accuracy of play at which to detect a suspicious game.")
    parser.add_argument("-n", "--topn", type=int, default=10, help="Number of players from the top to check.")

    args = parser.parse_args()

    print(f"* SUMMARY:")
    print(f"STOCKFISH PATH: {analysis.PATH} " + "[WORKING]" if analysis.engine != None else "[NOT WORKING]")
    print(f"Tournament ID: {args.tournament_id}")
    print(f"Accuracy Threshold: {args.threshold}%")
    print(f"Players to Check: Top {args.topn}")
    print("-" * 20)

    choice = input("Are you sure you want to continue? (y/N)")
    if (choice not in ['y', 'Y']): return

    # Get Top Players
    top_players = GetTopPlayers(args.tournament_id, args.topn)
    if not top_players:
        print("No players found or error fetching results. Exiting.")
        return

    print("-" * 20)
    print("Starting player game checks...")
    print("-" * 20)

    high_accuracy_found = False

    # Loop through players and check games
    for username in top_players:
        print(f"\nWaiting {API_DELAY_SECONDS}s before checking next player...")
        time.sleep(API_DELAY_SECONDS)

        player_games = GetPlayerGamesInTournament(username, args.tournament_id)

        if not player_games:
            print(f" -> No games found or error fetching games for {username}.")
            continue

        player_high_accuracy_count = 0
        for game in player_games:
            game_id = game.get('id', 'N/A')
            game_link = f"https://lichess.org/{game_id}"

            is_high, analysis_results, player_color = CheckGameAccuracy(game, username, args.threshold)

            if is_high:
                high_accuracy_found = True
                player_high_accuracy_count += 1

                print(f"** Player: {username}{player_color}, Game: {game_link}, Analysis: {analysis_results}%")
            else:
                print(f"Player: {username}{player_color}, Game: {game_link}, Analysis: {analysis_results}%")

        if player_high_accuracy_count == 0:
             print(f" -> No games found above {args.threshold}% accuracy for {username}.")


    print("-" * 20)
    if not high_accuracy_found:
        print(f"No games exceeding the accuracy threshold were found for the top {args.topn} players.")
    else:
        print("High accuracy game check finished.")
    print("-" * 20)


if __name__ == "__main__":
    main()