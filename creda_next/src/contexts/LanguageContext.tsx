'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

export type Language = 'english' | 'hindi' | 'tamil' | 'bengali' | 'marathi' | 'gujarati' | 'kannada' | 'malayalam' | 'punjabi' | 'telugu' | 'urdu';

export interface Translations {
  [key: string]: {
    [key in Language]: string;
  };
}

const translations: Translations = {
  'nav.dashboard': { english: 'Dashboard', hindi: 'डैशबोर्ड', tamil: 'கணக்குப் பலகை', bengali: 'ড্যাশবোর্ড', marathi: 'डॅशबोर्ड', gujarati: 'ડેશબોર્ડ', kannada: 'ಡ್ಯಾಶ್‌ಬೋರ್ಡ್', malayalam: 'ഡാഷ്‌ബോർഡ്', punjabi: 'ਡੈਸ਼ਬੋਰਡ', telugu: 'డ్యాష్‌బోర్డ్', urdu: 'ڈیش بورڈ' },
  'nav.portfolio': { english: 'Portfolio', hindi: 'पोर्टफोलियो', tamil: 'முதலீட்டு விவரங்கள்', bengali: 'পোর্টফোলিও', marathi: 'पोर्टफोलिओ', gujarati: 'પોર્ટફોલિયો', kannada: 'ಪೋರ್ಟ್‌ಫೋಲಿಯೋ', malayalam: 'പോർട്ട്‌ഫോളിയോ', punjabi: 'ਪੋਰਟਫੋਲੀਓ', telugu: 'పోర్ట్‌ఫోలియో', urdu: 'پورٹ فولیو' },
  'nav.budget': { english: 'Budget', hindi: 'बजट', tamil: 'பட்ஜெட்', bengali: 'বাজেট', marathi: 'बजेट', gujarati: 'બજેટ', kannada: 'ಬಜೆಟ್', malayalam: 'ബഡ്ജറ്റ്', punjabi: 'ਬਜਟ', telugu: 'బడ్జెట్', urdu: 'بجٹ' },
  'nav.voice': { english: 'Voice Assistant', hindi: 'वॉयस असिस्टेंट', tamil: 'குரல் உதவியாளர்', bengali: 'ভয়েস সহায়ক', marathi: 'आवाज सहायक', gujarati: 'વૉઇસ આસિસ્ટન્ટ', kannada: 'ಧ್ವನಿ ಸಹಾಯಕ', malayalam: 'വോയിസ് അസിസ്റ്റന്റ്', punjabi: 'ਅਵਾਜ਼ ਸਹਾਇਕ', telugu: 'వాయిస్ అసిస్టెంట్', urdu: 'وائس اسسٹنٹ' },
  'nav.advisory': { english: 'Advisory', hindi: 'सलाहकार', tamil: 'ஆலோசகர்', bengali: 'পরামর্শদাতা', marathi: 'सल्लागार', gujarati: 'સલાહકાર', kannada: 'ಸಲಹೆಗಾರ', malayalam: 'ഉപദേശകൻ', punjabi: 'ਸਲਾਹਕਾਰ', telugu: 'సలహాదారు', urdu: 'مشورہ' },
  'hero.title': { english: 'Your AI-Powered Financial Future', hindi: 'आपका AI-संचालित वित्तीय भविष्य', tamil: 'உங்கள் AI-இயக்கப்படும் நிதி எதிர்காலம்', bengali: 'আপনার AI-চালিত আর্থিক ভবিষ্যৎ', marathi: 'तुमचे AI-चालित आर्थिक भविष्य', gujarati: 'તમારું AI-સંચાલિત નાણાકીય ભવિષ્ય', kannada: 'ನಿಮ್ಮ AI-ಚಾಲಿತ ಆರ್ಥಿಕ ಭವಿಷ್ಯ', malayalam: 'നിങ്ങളുടെ AI-പവർഡ് സാമ്പത്തിക ഭാവി', punjabi: 'ਤੁਹਾਡਾ AI-ਸੰਚਾਲਿਤ ਵਿਤਤੀ ਭਵਿੱਖ', telugu: 'మీ AI-పవర్డ్ ఆర్థిక భవిష్యత్తు', urdu: 'آپ کا AI پر مبنی مالی مستقبل' },
  'hero.subtitle': { english: 'Speak naturally in any Indian language. Get instant, personalized financial advice powered by advanced AI and regulatory compliance.', hindi: 'किसी भी भारतीय भाषा में स्वाभाविक रूप से बोलें। उन्नत AI और नियामक अनुपालन द्वारा संचालित तत्काल, व्यक्तिगत वित्तीय सलाह प्राप्त करें।', tamil: 'எந்த இந்திய மொழியிலும் இயல்பாக பேசுங்கள்.', bengali: 'যেকোনো ভারতীয় ভাষায় স্বাভাবিকভাবে কথা বলুন।', marathi: 'कोणत्याही भारतीय भाषेत नैसर्गिकरित्या बोला.', gujarati: 'કોઈપણ ભારતીય ભાષામાં કુદરતી રીતે બોલો.', kannada: 'ಯಾವುದೇ ಭಾರತೀಯ ಭಾಷೆಯಲ್ಲಿ ಸ್ವಾಭಾವಿಕವಾಗಿ ಮಾತನಾಡಿ.', malayalam: 'ഏതു ഭാരതീയ ഭാഷയിലും സ്വാഭാവികമായി സംസാരിക്കുക.', punjabi: 'ਕਿਸੇ ਵੀ ਭਾਰਤੀ ਭਾਸ਼ਾ ਵਿੱਚ ਕੁਦਰਤੀ ਤੌਰ ਤੇ ਬੋਲੋ।', telugu: 'ఏ భారతీయ భాషలోనైనా సహజంగా మాట్లాడండి.', urdu: 'کسی بھی ہندوستانی زبان میں قدرتی طور پر بات کریں۔' },
  'voice.activate': { english: 'Say "Hey Creda" to activate', hindi: '"हे क्रेडा" कहकर सक्रिय करें', tamil: '"ஹே க்ரேடா" என்று சொல்லி செயல்படுத்துங்கள்', bengali: '"হে ক্রেডা" বলে সক্রিয় করুন', marathi: '"हे क्रेडा" म्हणून सक्रिय करा', gujarati: '"હે ક્રેડા" કહીને સક્રિય કરો', kannada: '"ಹೇ ಕ್ರೆಡಾ" ಎಂದು ಹೇಳಿ ಸಕ್ರಿಯಗೊಳಿಸಿ', malayalam: '"ഹേ ക്രെഡ" എന്ന് പറഞ്ഞ് സജീവമാക്കുക', punjabi: '"ਹੇ ਕ੍ਰੇਡਾ" ਕਹਿ ਕੇ ਸਰਗਰਮ ਕਰੋ', telugu: '"హే క్రెడా" అని చెప్పి సక్రియం చేయండి', urdu: '"ہے کریڈا" کہہ کر فعال کریں' },
  'voice.listening': { english: 'Listening for commands in any language...', hindi: 'किसी भी भाषा में कमांड सुनना...', tamil: 'எந்த மொழியிலும் கட்டளைகளைக் கேட்கிறது...', bengali: 'যেকোনো ভাষায় কমান্ড শুনছি...', marathi: 'कोणत्याही भाषेत कमांड ऐकत आहे...', gujarati: 'કોઈપણ ભાષામાં આદેશ સાંભળી રહ્યું છે...', kannada: 'ಯಾವುದೇ ಭಾಷೆಯಲ್ಲಿ ಆಜ್ಞೆಗಳನ್ನು ಕೇಳುತ್ತಿದೆ...', malayalam: 'ഏത് ഭാഷയിലും കമാൻഡുകൾ കേൾക്കുന്നു...', punjabi: 'ਕਿਸੇ ਵੀ ਭਾਸ਼ਾ ਵਿੱਚ ਕਮਾਂਡ ਸੁਣ ਰਿਹਾ ਹੈ...', telugu: 'ఏ భాషలోనైనా కమాండ్‌లను వింటుంది...', urdu: 'کسی بھی زبان میں کمانڈز سن رہا ہے...' },
  'voice.supported_languages': { english: 'Supports all Indian languages with automatic translation', hindi: 'स्वचालित अनुवाद के साथ सभी भारतीय भाषाओं का समर्थन करता है', tamil: 'தானியங்கு மொழிபெயர்ப்புடன் அனைத்து இந்திய மொழிகளையும் ஆதரிக்கிறது', bengali: 'স্বয়ংক্রিয় অনুবাদ সহ সমস্ত ভারতীয় ভাষা সমর্থন করে', marathi: 'स्वयंचलित भाषांतरासह सर्व भारतीय भाषांना समर्थन देते', gujarati: 'સ્વચાલિત અનુવાદ સાથે બધી ભારતીય ભાષાઓને સમર્થન આપે છે', kannada: 'ಸ್ವಯಂಚಾಲಿತ ಅನುವಾದದೊಂದಿಗೆ ಎಲ್ಲಾ ಭಾರತೀಯ ಭಾಷೆಗಳನ್ನು ಬೆಂಬಲಿಸುತ್ತದೆ', malayalam: 'സ്വയമേവയുള്ള വിവർത്തനത്തോടൊപ്പം എല്ലാ ഇന്ഡ്യൻ ഭാഷകളേയും പിന്തുണയ്ക്കുന്നു', punjabi: 'ਸਵੈਚਲਿਤ ਅਨੁਵਾਦ ਨਾਲ ਸਾਰੀਆਂ ਭਾਰਤੀ ਭਾਸ਼ਾਵਾਂ ਦਾ ਸਮਰਥਨ ਕਰਦਾ ਹੈ', telugu: 'స్వయంచాలక అనువాదంతో అన్ని భారతీయ భాషలకు మద్దతు ఇస్తుంది', urdu: 'خودکار ترجمے کے ساتھ تمام ہندوستانی زبانوں کی حمایت کرتا ہے' },
  'action.getStarted': { english: 'Get Started', hindi: 'शुरू करें', tamil: 'தொடங்குங்கள்', bengali: 'শুরু করুন', marathi: 'सुरुवात करा', gujarati: 'શરૂઆત કરો', kannada: 'ആരംभిसಿ', malayalam: 'ആരംभിക്കുക', punjabi: 'ਸ਼ੁਰੂ ਕਰੋ', telugu: 'ప్రారంభించండి', urdu: 'شروع کریں' },
  'action.tryDemo': { english: 'Try Demo', hindi: 'डेमो आज़माएं', tamil: 'டெமோ முயற்சிக்கவும்', bengali: 'ডেমো ট্রাই করুন', marathi: 'डेमो करून पहा', gujarati: 'ડેમો અજમાવો', kannada: 'ಡೆಮೋ ಪ್ರಯತ್ನಿಸಿ', malayalam: 'ഡെമോ പരീക്ഷിക്കുക', punjabi: 'ਡੈਮੋ ਅਜ਼ਮਾਓ', telugu: 'డెమో ట్రై చేయండి', urdu: 'ڈیمو آزمائیں' },
};

interface LanguageContextType {
  currentLanguage: Language;
  setLanguage: (language: Language) => void;
  t: (key: string) => string;
  availableLanguages: { code: Language; name: string; nativeName: string }[];
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

const availableLanguages = [
  { code: 'english' as Language, name: 'English', nativeName: 'English' },
  { code: 'hindi' as Language, name: 'Hindi', nativeName: 'हिंदी' },
  { code: 'tamil' as Language, name: 'Tamil', nativeName: 'தமிழ்' },
  { code: 'bengali' as Language, name: 'Bengali', nativeName: 'বাংলা' },
  { code: 'marathi' as Language, name: 'Marathi', nativeName: 'मराठी' },
  { code: 'gujarati' as Language, name: 'Gujarati', nativeName: 'ગુજરાતી' },
  { code: 'kannada' as Language, name: 'Kannada', nativeName: 'ಕನ್ನಡ' },
  { code: 'malayalam' as Language, name: 'Malayalam', nativeName: 'മലയാളം' },
  { code: 'punjabi' as Language, name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ' },
  { code: 'telugu' as Language, name: 'Telugu', nativeName: 'తెలుగు' },
  { code: 'urdu' as Language, name: 'Urdu', nativeName: 'اردو' },
];

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentLanguage, setCurrentLanguage] = useState<Language>('english');

  useEffect(() => {
    const savedLanguage = localStorage.getItem('finvoice-language');
    if (savedLanguage && availableLanguages.some(lang => lang.code === savedLanguage)) {
      setCurrentLanguage(savedLanguage as Language);
    }
  }, []);

  const setLanguage = (language: Language) => {
    setCurrentLanguage(language);
    localStorage.setItem('finvoice-language', language);
  };

  const t = (key: string): string => {
    return translations[key]?.[currentLanguage] || translations[key]?.['english'] || key;
  };

  return (
    <LanguageContext.Provider value={{ currentLanguage, setLanguage, t, availableLanguages }}>
      {children}
    </LanguageContext.Provider>
  );
};

export default LanguageProvider;
