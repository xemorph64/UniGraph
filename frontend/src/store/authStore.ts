import { create } from 'zustand';

interface AuthState {
  user: { user_id: string; username: string; role: string } | null;
  token: string | null;
  login: (token: string, user: any) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
  hasPermission: (permission: string) => boolean;
}

const ROLE_PERMISSIONS: Record<string, string[]> = {
  INVESTIGATOR: ['read:alerts', 'read:cases', 'write:cases', 'read:graph', 'read:transactions'],
  SUPERVISOR: ['read:alerts', 'read:cases', 'write:cases', 'read:graph', 'read:transactions', 'approve:str', 'read:reports'],
  COMPLIANCE_OFFICER: ['read:alerts', 'read:cases', 'write:cases', 'read:graph', 'read:transactions', 'approve:str', 'read:reports', 'write:reports', 'submit:str'],
  ADMIN: ['*'],
};

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  login: (token, user) => {
    localStorage.setItem('jwt_token', token);
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem('jwt_token');
    set({ token: null, user: null });
  },
  isAuthenticated: () => !!get().token,
  hasPermission: (permission) => {
    const { user } = get();
    if (!user) return false;
    const perms = ROLE_PERMISSIONS[user.role] || [];
    return perms.includes('*') || perms.includes(permission);
  },
}));
