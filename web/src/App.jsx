import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';

import LandingPage from './LandingPage.jsx';
import OperatorDashboard from './OperatorDashboard.jsx';
import AnchorDashboard from './AnchorDashboard.jsx';
import SettlementScreen from './SettlementScreen.jsx';
import LedgerView from './LedgerView.jsx';
import AnchorMeterReading from './AnchorMeterReading.jsx';
import AnchorWeeklyBalance from './AnchorWeeklyBalance.jsx';
import AnchorInstructions from './AnchorInstructions.jsx';
import OperatorInstructions from './OperatorInstructions.jsx';

// Prefer build-time env var from Render; allow localStorage override for manual testing.
const API_URL = import.meta.env.VITE_API_URL || localStorage.getItem('API_URL') || 'http://localhost:4000';
const EXPLORER_BASE = import.meta.env.VITE_TX_EXPLORER_BASE || 'https://amoy.polygonscan.com/tx/';
const REGION_LABELS = {
  'region-1': 'Denver Metro',
  'region-2': 'region-2'
};

function useAuth(){
  const [user, setUser] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [userId, setUserId] = useState(localStorage.getItem('USER_ID') || '');
  const [regionId, setRegionId] = useState(localStorage.getItem('REGION_ID') || 'region-1');
  const [role, setRole] = useState(localStorage.getItem('PILOT_ROLE') || '');
  const [token, setToken] = useState(localStorage.getItem('AUTH_TOKEN') || '');

  const decodeToken = useCallback((tok)=>{
    if(!tok) return null;
    const parts = tok.split('.');
    if(parts.length !== 3) return null;
    try{
      const normalized = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(atob(normalized));
      return payload;
    }catch(_err){
      return null;
    }
  }, []);

  const api = useMemo(()=>{
    return axios.create({
      baseURL: API_URL,
      headers: token
        ? { Authorization: `Bearer ${token}` }
        : userId ? { 'x-user-id': userId } : {}
    });
  }, [token, userId]);

  const refresh = useCallback(async ()=>{
    if(!userId && !token) return;
    try{
      const { data } = await api.get('/me');
      setUser(data.user);
      setWallet(data.wallet);
      if(data.user?.regionId && data.user.regionId !== regionId){
        setRegionId(data.user.regionId);
        localStorage.setItem('REGION_ID', data.user.regionId);
      }
    }catch(err){
      console.warn('Refresh failed', err);
    }
  }, [api, userId, token, regionId]);

  useEffect(()=>{
    refresh();
  }, [refresh]);

  useEffect(()=>{
    if(!userId && token){
      const payload = decodeToken(token);
      if(payload?.sub){
        setUserId(payload.sub);
        if(payload.regionId){
          setRegionId(payload.regionId);
          localStorage.setItem('REGION_ID', payload.regionId);
        }
      }
    }
  }, [decodeToken, token, userId]);

  const login = useCallback(async (nextRole, password) => {
    const { data } = await axios.post(`${API_URL}/auth/pilot-login`, { role: nextRole, password });
    localStorage.setItem('USER_ID', data.user.id);
    const resolvedRegion = data.user.regionId || 'region-1';
    localStorage.setItem('REGION_ID', resolvedRegion);
    localStorage.setItem('PILOT_ROLE', nextRole);
    if(data.token){
      localStorage.setItem('AUTH_TOKEN', data.token);
      setToken(data.token);
    }
    setRegionId(resolvedRegion);
    setUserId(data.user.id);
    setUser(data.user);
    setWallet(null);
    setRole(nextRole);
  }, []);

  const logout = useCallback(()=>{
    localStorage.removeItem('USER_ID');
    localStorage.removeItem('REGION_ID');
    localStorage.removeItem('PILOT_ROLE');
    localStorage.removeItem('AUTH_TOKEN');
    setUser(null);
    setWallet(null);
    setUserId('');
    setRegionId('region-1');
    setRole('');
    setToken('');
  }, []);

  const loginWithEmail = useCallback(async (email, password)=>{
    const { data } = await axios.post(`${API_URL}/auth/login`, { email, password });
    localStorage.setItem('USER_ID', data.user.id);
    localStorage.setItem('REGION_ID', data.user.regionId || 'region-1');
    localStorage.setItem('AUTH_TOKEN', data.token);
    setUserId(data.user.id);
    setRegionId(data.user.regionId || 'region-1');
    setToken(data.token);
    setUser(data.user);
    setWallet(null);
    setRole('');
  }, []);

  const registerWithEmail = useCallback(async (email, password, name)=>{
    const { data } = await axios.post(`${API_URL}/auth/register`, {
      email,
      password,
      name: name || undefined
    });
    localStorage.setItem('USER_ID', data.user.id);
    localStorage.setItem('REGION_ID', data.user.regionId || 'region-1');
    localStorage.setItem('AUTH_TOKEN', data.token);
    setUserId(data.user.id);
    setRegionId(data.user.regionId || 'region-1');
    setToken(data.token);
    setUser(data.user);
    setWallet(null);
    setRole('');
  }, []);

  return { user, wallet, userId, regionId, role, api, login, loginWithEmail, registerWithEmail, logout, refresh };
}

const NAV_CONFIG = {
  operator: [
    { id: 'operator-dashboard', label: 'Dashboard' },
    { id: 'ledger', label: 'View Ledger' },
    { id: 'settlement', label: 'Settlement' },
    { id: 'operator-help', label: 'Help / Instructions' }
  ],
  anchor: [
    { id: 'anchor-dashboard', label: 'Dashboard' },
    { id: 'anchor-meter', label: 'Enter Meter Reading' },
    { id: 'ledger', label: 'View Ledger' },
    { id: 'anchor-balance', label: 'Weekly Balance Due' },
    { id: 'anchor-instructions', label: 'Instructions' }
  ]
};

export default function App(){
  const {
    user,
    wallet,
    userId,
    regionId,
    role,
    api,
    login,
    loginWithEmail,
    registerWithEmail,
    logout,
    refresh
  } = useAuth();
  const [view, setView] = useState(role === 'anchor' ? 'anchor-dashboard' : 'operator-dashboard');
  const [userPanelOpen, setUserPanelOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const triggerGlobalRefresh = useCallback(()=>{
    refresh();
    setRefreshKey((key)=>key + 1);
  }, [refresh]);

  useEffect(()=>{
    setRefreshKey((key)=> key + 1);
  }, [userId, regionId, role]);

  useEffect(()=>{
    if(role === 'anchor' && !view.startsWith('anchor') && view !== 'ledger'){
      setView('anchor-dashboard');
    }
    if(role === 'operator' && !view.startsWith('operator') && view !== 'ledger' && view !== 'settlement'){
      setView('operator-dashboard');
    }
  }, [role, view]);

  const walletBalance = wallet ? Number(wallet.balanceCents || 0) / 100 : 0;
  const regionLabel = REGION_LABELS[regionId] || regionId;
  const balanceLabel = (() => {
    if(!wallet) return '—';
    if(role === 'anchor' && walletBalance < 0){
      return `Owes $${Math.abs(walletBalance).toFixed(2)}`;
    }
    return `$${walletBalance.toFixed(2)} ${role === 'anchor' ? 'balance' : 'available'}`;
  })();

  const navItems = NAV_CONFIG[role] || [];

  if(!userId){
    return (
      <LandingPage
        onPilotLogin={login}
        onEmailLogin={loginWithEmail}
        onEmailRegister={registerWithEmail}
      />
    );
  }

  return (
    <>
      <header className="app-header">
        <div className="app-hero">
          <div className="app-hero__copy">
            <span className="app-header__brand">KORA</span>
            <span className="app-header__sub">Pilot operator cockpit</span>
          </div>
        </div>
        <nav className="app-tabs">
          <div className="app-tabs__group">
            {navItems.map((item)=>(
              <button
                key={item.id}
                type="button"
                className={`pill pill--nav ${view === item.id ? 'active' : ''}`}
                onClick={()=>setView(item.id)}
              >
                {item.label}
              </button>
            ))}
            <button type="button" className="pill pill--ghost" onClick={logout}>Log out</button>
          </div>
        </nav>
      </header>

      {user && (
        <aside className={`user-tab ${userPanelOpen ? 'user-tab--open' : ''}`}>
          <button
            type="button"
            className="user-tab__toggle"
            onClick={()=>setUserPanelOpen((open)=>!open)}
            aria-expanded={userPanelOpen}
          >
            <span className="user-tab__toggle-text">{userPanelOpen ? 'Close' : 'Info'}</span>
            <span className="user-tab__toggle-arrow">{userPanelOpen ? '<' : '>'}</span>
          </button>
          <div className="user-tab__body">
            <span className="user-tab__title">Account snapshot</span>
            <dl className="user-tab__list">
              <div className="user-tab__item">
                <dt>Name</dt>
                <dd>{user?.name || user?.email}</dd>
              </div>
              <div className="user-tab__item">
                <dt>Region</dt>
                <dd>{regionLabel}</dd>
              </div>
              <div className="user-tab__item">
                <dt>Balance</dt>
                <dd>{balanceLabel}</dd>
              </div>
            </dl>
          </div>
        </aside>
      )}

      <main>
        {view === 'operator-dashboard' && (
          <OperatorDashboard
            api={api}
            refreshKey={refreshKey}
            onGlobalRefresh={triggerGlobalRefresh}
          />
        )}
        {view === 'anchor-dashboard' && (
          <AnchorDashboard
            api={api}
            refreshKey={refreshKey}
            onGlobalRefresh={triggerGlobalRefresh}
          />
        )}
        {view === 'anchor-meter' && (
          <AnchorMeterReading
            api={api}
            refreshKey={refreshKey}
            onGlobalRefresh={triggerGlobalRefresh}
          />
        )}
        {view === 'anchor-balance' && (
          <AnchorWeeklyBalance
            api={api}
            refreshKey={refreshKey}
            onGlobalRefresh={triggerGlobalRefresh}
          />
        )}
        {view === 'anchor-instructions' && (
          <AnchorInstructions />
        )}
        {view === 'settlement' && (
          <SettlementScreen
            api={api}
            refreshKey={refreshKey}
            explorerBase={EXPLORER_BASE}
          />
        )}
        {view === 'operator-help' && (
          <OperatorInstructions />
        )}
        {view === 'ledger' && (
          <LedgerView
            api={api}
            refreshKey={refreshKey}
            explorerBase={EXPLORER_BASE}
          />
        )}
      </main>
    </>
  );
}
