from game.game_engine import GameEngine

if __name__ == "__main__":
    game = GameEngine()
    try:
        game.run()
    except KeyboardInterrupt:
        print("\nThe cold watches you go...\n")