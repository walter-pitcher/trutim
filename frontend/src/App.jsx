import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { UserStatusProvider } from './context/UserStatusContext';
import Login from './pages/Login';
import Register from './pages/Register';
import MainLayout from './components/MainLayout';
import Dashboard from './pages/Dashboard';
import CompanyRoom from './pages/CompanyRoom';
import ContactRoom from './pages/ContactRoom';
import Profile from './pages/Profile';
import WorldMap from './pages/WorldMap';
import './App.css';

function RoomRedirect() {
  const { id } = useParams();
  return <Navigate to={`/company/${id}`} replace />;
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen"><div className="spinner" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <UserStatusProvider>
        <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="company/:id" element={<CompanyRoom />} />
            <Route path="contact/:userId" element={<ContactRoom />} />
            <Route path="room/:id" element={<RoomRedirect />} />
            <Route path="profile" element={<Profile />} />
            <Route path="map" element={<WorldMap />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
        </UserStatusProvider>
    </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
