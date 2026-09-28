#!/usr/bin/env python3
"""
Interactive & Command-Line TODO Application
Features: Add, Remove, Toggle Done/Undone, List, Filter, Search, and Priority Tags.
"""

import sys
import json
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json")

def load_todos():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_todos(todos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, indent=2)

def add_task(title, priority="medium", due_date=""):
    todos = load_todos()
    new_id = max([t.get("id", 0) for t in todos], default=0) + 1
    task = {
        "id": new_id,
        "title": title.strip(),
        "done": False,
        "priority": priority.lower(),
        "due_date": due_date,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    todos.append(task)
    save_todos(todos)
    print(f"✅ Added task #{new_id}: '{title}' [{priority.upper()}]")

def remove_task(task_id):
    todos = load_todos()
    initial_len = len(todos)
    todos = [t for t in todos if t.get("id") != task_id]
    if len(todos) < initial_len:
        save_todos(todos)
        print(f"🗑️  Removed task #{task_id}.")
    else:
        print(f"⚠️  Task #{task_id} not found.")

def mark_done(task_id, done=True):
    todos = load_todos()
    found = False
    for task in todos:
        if task.get("id") == task_id:
            task["done"] = done
            found = True
            status_str = "completed" if done else "active"
            print(f"✨ Task #{task_id} marked as {status_str}.")
            break
    if found:
        save_todos(todos)
    else:
        print(f"⚠️  Task #{task_id} not found.")

def list_tasks(filter_status="all", search_query=None):
    todos = load_todos()
    if not todos:
        print("\n📭 No tasks found! Use 'add' to create one.\n")
        return

    filtered = todos
    if filter_status == "active":
        filtered = [t for t in filtered if not t.get("done")]
    elif filter_status == "done":
        filtered = [t for t in filtered if t.get("done")]

    if search_query:
        filtered = [t for t in filtered if search_query.lower() in t.get("title", "").lower()]

    print("\n" + "=" * 65)
    print(f"📋 TODO LIST ({len(filtered)} items | Filter: {filter_status})")
    print("=" * 65)

    if not filtered:
        print("  (No matching tasks)")
    else:
        for t in filtered:
            status = "✅ [DONE]" if t.get("done") else "⭕ [TODO]"
            prio = t.get("priority", "medium").upper()
            due = f" | Due: {t.get('due_date')}" if t.get("due_date") else ""
            print(f"  {t['id']:2d}. {status} [{prio:6s}] {t['title']}{due}")
    
    total = len(todos)
    done_count = sum(1 for t in todos if t.get("done"))
    print("-" * 65)
    print(f"Summary: {done_count}/{total} completed\n")

def interactive_mode():
    while True:
        print("\n--- TODO MANAGER ---")
        print("1. List All Tasks")
        print("2. Add Task")
        print("3. Mark Task as Done")
        print("4. Mark Task as Pending")
        print("5. Delete Task")
        print("6. Exit")
        choice = input("Select an option (1-6): ").strip()

        if choice == "1":
            list_tasks()
        elif choice == "2":
            title = input("Task title: ").strip()
            if title:
                prio = input("Priority (low/medium/high) [medium]: ").strip() or "medium"
                due = input("Due date (YYYY-MM-DD, optional): ").strip()
                add_task(title, prio, due)
        elif choice == "3":
            try:
                tid = int(input("Task ID to mark done: "))
                mark_done(tid, True)
            except ValueError:
                print("Invalid ID.")
        elif choice == "4":
            try:
                tid = int(input("Task ID to mark pending: "))
                mark_done(tid, False)
            except ValueError:
                print("Invalid ID.")
        elif choice == "5":
            try:
                tid = int(input("Task ID to remove: "))
                remove_task(tid)
            except ValueError:
                print("Invalid ID.")
        elif choice == "6":
            print("Goodbye! 👋")
            break
        else:
            print("Invalid choice. Try again.")

def main():
    if len(sys.argv) == 1:
        interactive_mode()
        return

    cmd = sys.argv[1].lower()
    if cmd in ("list", "ls"):
        status = sys.argv[2] if len(sys.argv) > 2 else "all"
        list_tasks(filter_status=status)
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: python todo.py add \"Task description\" [priority] [due_date]")
            return
        title = sys.argv[2]
        priority = sys.argv[3] if len(sys.argv) > 3 else "medium"
        due = sys.argv[4] if len(sys.argv) > 4 else ""
        add_task(title, priority, due)
    elif cmd in ("done", "complete"):
        if len(sys.argv) < 3:
            print("Usage: python todo.py done <task_id>")
            return
        try:
            mark_done(int(sys.argv[2]), True)
        except ValueError:
            print("Task ID must be a number.")
    elif cmd == "undone":
        if len(sys.argv) < 3:
            print("Usage: python todo.py undone <task_id>")
            return
        try:
            mark_done(int(sys.argv[2]), False)
        except ValueError:
            print("Task ID must be a number.")
    elif cmd in ("remove", "rm", "delete"):
        if len(sys.argv) < 3:
            print("Usage: python todo.py remove <task_id>")
            return
        try:
            remove_task(int(sys.argv[2]))
        except ValueError:
            print("Task ID must be a number.")
    else:
        print(f"Unknown command: {cmd}")
        print("Available commands: list, add, done, undone, remove")

if __name__ == "__main__":
    main()
