import type { Metadata } from 'next';
import AuthPage from '@/components/auth/AuthPage';

export const metadata: Metadata = {
  title: 'Create Account',
  description: 'Create your free CREDA account. AI-powered financial intelligence for the Indian investor.',
};

export default function SignUpPage() {
  return <AuthPage mode="sign-up" />;
}
