from dataclasses import asdict
from datetime import datetime
import json
import os
from typing import List, Tuple
from time import sleep
from utils.states import GameState, PlayerState

def synchronize_start_time(gs: GameState, ps: PlayerState) -> None:
    """
    Synchronizes the start time between players, assigning the current player as the timekeeper
    if the start time file does not exist.
    """
    # Check if the start time file already exists
    if not os.path.exists(gs.start_time_path):
        # Load players to ensure the list is up to date
        gs.players = load_players_from_lobby(gs)
        
        # Assign the current player as the timekeeper
        ps.timekeeper = True

        # Create the start time file
        init_game_file(gs.start_time_path)

        # Write the start time to the file
        ps.starttime = datetime.now().replace(tzinfo=None)
        start_time_str = ps.starttime.strftime("%Y-%m-%d %H:%M:%S")
        with open(gs.start_time_path, "w") as f:
            f.write(start_time_str)

    else:
        # If not the timekeeper, wait for the file to exist
        while not os.path.exists(gs.start_time_path):
            print("Waiting for the timekeeper to initialize the start time...")
            sleep(1)

        # Load the starting time from the file
        with open(gs.start_time_path, "r") as f:
            start_time_str = f.read().strip()
            ps.starttime = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            ps.starttime = ps.starttime.replace(tzinfo=None)  # Remove timezone info


def init_game_file(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("")  # Start fresh

# def append_message(path: str, message: str) -> None:
#     with open(path, "a", encoding="utf-8") as f:
#         f.write(message + "\n")
#         f.flush()
#         os.fsync(f.fileno())

def read_new_messages(path: str, last_line: int) -> Tuple[List[str], List[str], int]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    full_chat_list = [line.strip() for line in lines if line.strip()]
    new_messages_list = full_chat_list[last_line:]
    new_message_count = len(new_messages_list)
    last_line += new_message_count
    return full_chat_list, new_messages_list, last_line

class SequentialAssigner:
    def __init__(self, list_path: str, index_path: str, key: str):
        # print(f"Loading items from {list_path}...")
        self.list_path = list_path
        self.index_path = index_path
        self.key = key
        self.items = self._load_items()

    def _load_items(self) -> List[str]:
        if not os.path.exists(self.list_path):
            raise FileNotFoundError(f"Missing data file: {self.list_path}")

        try:
            with open(self.list_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate the JSON structure
                if self.key not in data or not isinstance(data[self.key], list):
                    raise ValueError(f"Invalid JSON format: {self.key} list not found")
                items = [item.strip().upper() for item in data[self.key] if item.strip()]
        except (json.JSONDecodeError, IOError) as e:
            raise IOError(f"Error reading JSON file: {e}")

        if not items:
            raise ValueError(f"List at {self.list_path} is empty or contains only invalid items.")

        return items

    def _read_index(self) -> int:
        if not os.path.exists(self.index_path):
            return 0

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                idx = int(f.read().strip())
            if not (0 <= idx < len(self.items)):
                raise ValueError("Index out of range.")
            return idx
        except (ValueError, IOError):
            return 0

    def _write_index(self, idx: int):
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                f.write(str(idx))
        except Exception as e:
            print(f"Error writing index file: {e}")

    def assign(self) -> str:
        idx = self._read_index()
        selected_item = self.items[idx]
        if not selected_item or selected_item not in self.items:
            print(f"Warning: Invalid or empty item selected: '{selected_item}'")
            selected_item = self.items[0]  # Default to the first item as a fallback
        next_idx = (idx + 1) % len(self.items)
        self._write_index(next_idx)

        # Get the caller's file name and line number\
        # FOR DEBUGGING UNCOMMENT BELOW
        # caller_frame = inspect.currentframe().f_back
        # file_name = caller_frame.f_code.co_filename
        # line_number = caller_frame.f_lineno

        # print(f"Assigned {self.key[-1]}: {selected_item} (called from {file_name}, line {line_number})")
        return selected_item


def save_player_to_lobby_file(ps: PlayerState) -> None:
    """
    Save a player to the shared players.json for their lobby.
    """
    lobby_path = f"./data/runtime/lobbies/lobby_{ps.lobby_id}"
    os.makedirs(lobby_path, exist_ok=True)
    file_path = os.path.join(lobby_path, "players.json")

    players = []

    # Load existing players if file exists
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                players = json.load(f)
            except json.JSONDecodeError:
                pass  # start fresh if it's corrupt or empty

    # Avoid duplicates by code_name
    if not any(p["code_name"] == ps.code_name for p in players):
        players.append(asdict(ps))

    # Save updated list
    with open(file_path, "w") as f:
        json.dump(players, f, indent=2)

def load_players_from_lobby(gs:GameState) -> list[PlayerState]:
    if not os.path.exists(gs.player_path):
        return []

    with open(gs.player_path, "r") as f:
        data = json.load(f)
        return [PlayerState(**p) for p in data]
