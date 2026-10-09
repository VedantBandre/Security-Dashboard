import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchSession, setCsrfToken, signIn, signInDemo, signOut } from '../api';
import { SessionContext } from './SessionContext';

export default function SessionProvider({ children }) {
  const [session, setSession] = useState({ user: null, demo: null, loading: true, error: null });
  const generation = useRef(0);
  const accept = useCallback(data => {
    setCsrfToken(data.csrf_token);
    setSession({ user: data.user, demo: data.demo || null, loading: false, error: null });
  }, []);
  const refreshSession = useCallback(async () => {
    const current = ++generation.current;
    try { const data = await fetchSession(); if (current === generation.current) accept(data); }
    catch (error) { if (current === generation.current) setSession(previous => ({ ...previous, loading: false, error: error.message })); }
  }, [accept]);
  useEffect(() => {
    refreshSession();
    const expired = () => { generation.current += 1; setSession({ user: null, demo: null, loading: false, error: null }); refreshSession(); };
    const focused = () => { if (document.visibilityState !== 'hidden') refreshSession(); };
    window.addEventListener('session-expired', expired);
    window.addEventListener('session-recheck', refreshSession);
    window.addEventListener('focus', focused);
    return () => { generation.current += 1; window.removeEventListener('session-expired', expired); window.removeEventListener('session-recheck', refreshSession); window.removeEventListener('focus', focused); };
  }, [refreshSession]);
  async function login(data) { generation.current += 1; const next = await signIn(data); accept(next); }
  async function loginDemo() { generation.current += 1; const next = await signInDemo(); accept(next); }
  async function logout() { generation.current += 1; const next = await signOut(); accept(next); }
  return <SessionContext.Provider value={{ ...session, login, loginDemo, logout, refreshSession }}>{children}</SessionContext.Provider>;
}
