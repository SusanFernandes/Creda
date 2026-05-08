import type { Metadata } from 'next';
import AuthPage from '@/components/auth/AuthPage';

export const metadata: Metadata = {
  title: 'Sign In',
  description: 'Sign in to CREDA — your AI-powered financial intelligence platform.',
};

export default function SignInPage() {
  return <AuthPage mode="sign-in" />;
}
