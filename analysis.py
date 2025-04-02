from stockfish import Stockfish
import chess

# We will use a local installation of
# stockfish to evaluate the game.
# By counting the number of "mistakes"
# and the number of "perfect" moves
# the player makes we will have a decent
# idea of whether they could be cheating.
#
# As per lichess's specifications:
# 100 CPL is a "mistake".
# And for our use case,
# we will consider <20 CPL to be a perfect move
# (CPL = Centipawn Loss)

PATH = open('stockfish-path.txt', 'r').read()

engine = Stockfish(path=PATH)

# Returns "analysis" dictionary with
# 'perfect_moves', 'mistakes', and 'accuracy'
def AnalyzeGame(PGN, isWhite):
    try:
        analysis = {
            'perfect_moves' : 0,
            'decent_moves'  : 0,
            'mistakes'      : 0,
            'accuracy'      : 0.0
        }
        
        engine.set_fen_position('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1') # reset engine position
        converter = chess.Board()
        moves = PGN.split(' ')
        white_to_play = True
        played_moves = 0
        for move in moves:
            if white_to_play == isWhite:
                played_moves += 1
                current_centipawn = engine.get_evaluation()['value']
                uci_move = converter.push_san(move).uci()
                engine.make_moves_from_current_position([uci_move])
                next_centipawn = engine.get_evaluation()['value']

                centipawn_loss = (current_centipawn - next_centipawn) * (1 if isWhite else -1)

                if centipawn_loss < 30:
                    analysis['perfect_moves'] += 1
                elif centipawn_loss > 100:
                    analysis['mistakes'] += 1
                else:
                    analysis['decent_moves'] += 1
            else:
                # Just play the oppoenent's move
                uci_move = converter.push_san(move).uci()
                engine.make_moves_from_current_position([uci_move])

            white_to_play = not white_to_play
            

        # Rough accuracy metric in percentage
        analysis['accuracy'] = ( (analysis['perfect_moves'] + analysis['decent_moves'] * 0.5) / played_moves ) * 100
        analysis['accuracy'] = round(analysis['accuracy'], 2)

        return analysis
    except Exception as e:
        print("-" * 20)
        print(f"** ERROR ANALYZING GAME: {e}\nGAME: {PGN}")
        print("-" * 20)
        return analysis

# if __name__ == "__main__":
#     isWhite = input("Is white? (Y/n)")
#     pgn = input("Plain PGN (e4 e5 nf3 nc6...): ")
#     print(AnalyzeGame(pgn, isWhite.lower() != 'n'))