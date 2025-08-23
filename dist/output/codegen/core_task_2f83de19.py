import tkinter as tk
from tkinter import messagebox
import random
import json
import os

class BettingApp:
    def __init__(self, master):
        self.master = master
        master.title("Kentucky Derby Betting App")

        self.horses = ["Thunderbolt", "Storm Chaser", "Lucky Charm", "Speedster", "Black Beauty"]
        self.odds = {horse: round(random.uniform(1.5, 15.0), 2) for horse in self.horses}

        self.label = tk.Label(master, text="Kentucky Derby Betting Odds")
        self.label.pack()

        self.odds_text = tk.Text(master, height=10, width=30)
        self.odds_text.pack()
        self.display_odds()

        self.bet_label = tk.Label(master, text="Enter your bet amount:")
        self.bet_label.pack()

        self.bet_entry = tk.Entry(master)
        self.bet_entry.pack()

        self.place_bet_button = tk.Button(master, text="Place Bet", command=self.place_bet)
        self.place_bet_button.pack()

    def display_odds(self):
        self.odds_text.delete(1.0, tk.END)
        for horse, odds in self.odds.items():
            self.odds_text.insert(tk.END, f"{horse}: {odds} to 1\n")

    def place_bet(self):
        bet_amount = self.bet_entry.get()
        if not bet_amount.isdigit():
            messagebox.showerror("Invalid Input", "Please enter a valid bet amount.")
            return
        bet_amount = int(bet_amount)
        selected_horse = random.choice(self.horses)
        payout = bet_amount * self.odds[selected_horse]
        messagebox.showinfo("Bet Placed", f"You placed a bet of ${bet_amount} on {selected_horse}. Potential payout: ${payout:.2f}")

def main():
    root = tk.Tk()
    app = BettingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

# Code to create executable using pyinstaller
# To generate the executable, run the following command in terminal:
# pyinstaller --onefile --windowed your_script_name.py
# Replace `your_script_name.py` with the name of your Python file.