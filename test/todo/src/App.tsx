import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  completed: boolean;
}

export const App: React.FC = () => {
  const [todos, setTodos] = useState<Todo[]>([
    { id: 1, text: 'Learn React & Vite', completed: true },
    { id: 2, text: 'Build an awesome app with PIHU', completed: false },
    { id: 3, text: 'Deploy project', completed: false },
  ]);
  const [input, setInput] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  const addTodo = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    const newTodo: Todo = {
      id: Date.now(),
      text: input.trim(),
      completed: false,
    };
    setTodos([...todos, newTodo]);
    setInput('');
  };

  const toggleTodo = (id: number) => {
    setTodos(todos.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
  };

  const deleteTodo = (id: number) => {
    setTodos(todos.filter(t => t.id !== id));
  };

  const filteredTodos = todos.filter(t => {
    if (filter === 'active') return !t.completed;
    if (filter === 'completed') return t.completed;
    return true;
  });

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#0f172a',
      color: '#f8fafc',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '40px 20px',
      boxSizing: 'border-box'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '520px',
        background: '#1e293b',
        borderRadius: '16px',
        padding: '28px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3)',
      }}>
        <header style={{ marginBottom: '24px', textAlign: 'center' }}>
          <h1 style={{ fontSize: '28px', fontWeight: '800', margin: '0 0 8px 0', background: 'linear-gradient(135deg, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Todo App
          </h1>
          <p style={{ color: '#94a3b8', margin: 0, fontSize: '14px' }}>
            Organize your tasks efficiently
          </p>
        </header>

        <form onSubmit={addTodo} style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Add a new task..."
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: '8px',
              border: '1px solid #334155',
              background: '#0f172a',
              color: '#f8fafc',
              fontSize: '15px',
              outline: 'none',
            }}
          />
          <button
            type="submit"
            style={{
              padding: '12px 20px',
              borderRadius: '8px',
              border: 'none',
              background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
              color: '#ffffff',
              fontSize: '15px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'opacity 0.2s',
            }}
          >
            Add
          </button>
        </form>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginBottom: '20px' }}>
          {(['all', 'active', 'completed'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '6px 14px',
                borderRadius: '20px',
                border: 'none',
                background: filter === f ? '#38bdf8' : '#334155',
                color: filter === f ? '#0f172a' : '#94a3b8',
                fontWeight: filter === f ? '700' : '500',
                textTransform: 'capitalize',
                cursor: 'pointer',
                fontSize: '13px',
                transition: 'all 0.2s'
              }}
            >
              {f}
            </button>
          ))}
        </div>

        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {filteredTodos.length === 0 ? (
            <li style={{ textAlign: 'center', color: '#64748b', padding: '24px 0' }}>
              No tasks found
            </li>
          ) : (
            filteredTodos.map((todo) => (
              <li
                key={todo.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  background: '#0f172a',
                  border: '1px solid #334155',
                }}
              >
                <div
                  onClick={() => toggleTodo(todo.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    cursor: 'pointer',
                    flex: 1,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={todo.completed}
                    onChange={() => {}}
                    style={{
                      width: '18px',
                      height: '18px',
                      cursor: 'pointer',
                      accentColor: '#38bdf8'
                    }}
                  />
                  <span
                    style={{
                      fontSize: '15px',
                      color: todo.completed ? '#64748b' : '#f8fafc',
                      textDecoration: todo.completed ? 'line-through' : 'none',
                      transition: 'all 0.2s',
                    }}
                  >
                    {todo.text}
                  </span>
                </div>
                <button
                  onClick={() => deleteTodo(todo.id)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#ef4444',
                    cursor: 'pointer',
                    fontSize: '18px',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    lineHeight: 1
                  }}
                  title="Delete"
                >
                  ✕
                </button>
              </li>
            ))
          )}
        </ul>

        <footer style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid #334155', display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '13px' }}>
          <span>{todos.filter(t => !t.completed).length} items left</span>
          <span>{todos.filter(t => t.completed).length} completed</span>
        </footer>
      </div>
    </div>
  );
};
