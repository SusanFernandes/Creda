import { useRouter }       from "expo-router";
import { useEffect, useState, useRef, useCallback } from "react";
import { View, ScrollView, TouchableOpacity, Animated } from "react-native";
import { SafeAreaView }   from "react-native-safe-area-context";
import * as Speech        from "expo-speech";
import { Gradient }       from "~/components/Gradient";
import { ApiService }     from "~/services/api";
import { useVoiceController } from "~/hooks/useVoiceController";
import {
  useMonthlySpend, useBillsDueCount, usePortfolioSummary,
  useTransactions, useGoals, useHoldingsWithAssets,
} from "~/hooks/queries";
import { P, Small, H4 } from "~/components/ui/typography";
import { Mic, MicOff, MessageCircle, Zap, Loader2, Volume2 } from "lucide-react-native";

interface Message { id: string; text: string; isUser: boolean; timestamp: Date; }

// Screen → path for TEXT-based navigation intents (from LangGraph /chat)
const TEXT_NAV_ROUTES: Record<string, string> = {
  home:          "/(protected)/(drawer)/(tabs)",
  dashboard:     "/(protected)/(drawer)/(tabs)",
  portfolio:     "/(protected)/(drawer)/(tabs)/investments",
  investments:   "/(protected)/(drawer)/(tabs)/investments",
  expenses:      "/(protected)/(drawer)/(tabs)/expenses",
  bills:         "/(protected)/(drawer)/(tabs)/bills",
  budget:        "/(protected)/(drawer)/budgets",
  goals:         "/(protected)/(drawer)/goals",
  knowledge:     "/(protected)/(drawer)/knowledge",
  insurance:     "/(protected)/(drawer)/insurance",
  fraud:         "/(protected)/(drawer)/fraud",
};

// Typing indicator
const TypingIndicator = ({ visible }: { visible: boolean }) => {
  const dot1 = useRef(new Animated.Value(0.3)).current;
  const dot2 = useRef(new Animated.Value(0.3)).current;
  const dot3 = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    if (!visible) return;
    const animate = () =>
      Animated.sequence([
        Animated.timing(dot1, { toValue: 1, duration: 400, useNativeDriver: true }),
        Animated.timing(dot2, { toValue: 1, duration: 400, useNativeDriver: true }),
        Animated.timing(dot3, { toValue: 1, duration: 400, useNativeDriver: true }),
        Animated.timing(dot1, { toValue: 0.3, duration: 400, useNativeDriver: true }),
        Animated.timing(dot2, { toValue: 0.3, duration: 400, useNativeDriver: true }),
        Animated.timing(dot3, { toValue: 0.3, duration: 400, useNativeDriver: true }),
      ]).start(() => { if (visible) animate(); });
    animate();
  }, [visible, dot1, dot2, dot3]);

  if (!visible) return null;
  return (
    <View className="flex-row justify-start mb-4">
      <View className="bg-card border border-border rounded-2xl rounded-bl-sm py-3 px-4 ml-12 shadow-sm">
        <View className="flex-row items-center">
          {[dot1, dot2, dot3].map((d, i) => (
            <Animated.View key={i} style={{ opacity: d }}
              className="w-2 h-2 bg-muted-foreground rounded-full mx-0.5" />
          ))}
        </View>
      </View>
      <View className="w-8 h-8 bg-primary rounded-full items-center justify-center absolute left-0 bottom-0 shadow-sm">
        <MessageCircle size={16} color="white" />
      </View>
    </View>
  );
};

export default function AgentScreen() {
  const [messages,  setMessages]  = useState<Message[]>([]);
  const [isTyping,  setIsTyping]  = useState(false);
  const scrollViewRef             = useRef<ScrollView>(null);
  const router                    = useRouter();
  const sessionIdRef              = useRef(`app_${Date.now()}`);

  const { data: spend        = 0 } = useMonthlySpend();
  const { data: billsDue     = 0 } = useBillsDueCount();
  const { data: summary          } = usePortfolioSummary();
  const { data: transactions = [] } = useTransactions();
  const { data: goals        = [] } = useGoals();
  const { data: holdings     = [] } = useHoldingsWithAssets();

  const addBotMessage = useCallback((text: string) =>
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), text, isUser: false, timestamp: new Date() },
    ]), []);

  // ── sendToBackend: text input + voice conversation fallback ────────────────
  const sendToBackend = useCallback(async (text: string) => {
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), text, isUser: true, timestamp: new Date() },
    ]);
    setIsTyping(true);

    try {
      const chatRes = await ApiService.chat({
        message:   text,
        user_id:   "app_user",
        session_id: sessionIdRef.current,
        language:  "english",
        user_profile: {
          monthly_spend:  spend,
          bills_due:      billsDue,
          portfolio_value: summary?.value ?? 0,
          active_goals:   goals.filter((g: any) => g.status === "active").length,
        },
        portfolio_data: {
          holdings:            holdings.slice(0, 10),
          recent_transactions: transactions.slice(-5),
        },
      });

      if (chatRes.intent === "navigation" && chatRes.data?.screen) {
        const path = TEXT_NAV_ROUTES[chatRes.data.screen as string];
        if (path) {
          router.push(path as any);
          addBotMessage(`Navigating to ${chatRes.data.screen}\u2026`);
          Speech.speak(`Navigating to ${chatRes.data.screen}`, { language: "en-IN", rate: 0.9 });
          return;
        }
      }

      addBotMessage(chatRes.response);
      Speech.speak(chatRes.response, { language: "en-IN", rate: 0.88 });
    } catch {
      addBotMessage("Sorry, I could not reach the server. Please check your connection.");
    } finally {
      setIsTyping(false);
    }
  }, [spend, billsDue, summary, goals, holdings, transactions, router, addBotMessage]);

  // ── Voice controller (PTT + VAD + Groq function-calling) ──────────────────
  // When the LLM decides it is a conversational answer (not navigation),
  // the transcript is forwarded to sendToBackend for a full LangGraph response.
  const {
    status: voiceStatus,
    isListening,
    transcript,
    startListening,
    stopListening,
  } = useVoiceController("app_user", "en", sendToBackend);

  // Scroll on new messages
  useEffect(() => {
    setTimeout(() => scrollViewRef.current?.scrollToEnd({ animated: true }), 100);
  }, [messages]);

  // Welcome message
  useEffect(() => {
    addBotMessage(
      "Hello! I am your Creda AI assistant. " +
      "Tap the big mic button to speak, or choose a quick action. " +
      "You can say things like \u201cmera portfolio dikhao\u201d or \u201cSIP calculate karo\u201d."
    );
  }, []);

  const formatTime = (d: Date) =>
    d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const renderMessage = (msg: Message) => (
    <View key={msg.id} className={`mb-4 ${msg.isUser ? "items-end" : "items-start"}`}>
      <View className={`flex-row ${msg.isUser ? "flex-row-reverse" : "flex-row"} items-end max-w-[85%]`}>
        {!msg.isUser && (
          <View className="w-8 h-8 bg-primary rounded-full items-center justify-center mr-3 shadow-sm">
            <MessageCircle size={16} color="white" />
          </View>
        )}
        <View className={`${msg.isUser ? "bg-primary" : "bg-card border border-border"} ${
          msg.isUser ? "rounded-2xl rounded-br-sm" : "rounded-2xl rounded-bl-sm"
        } px-4 py-3 shadow-sm`}>
          <P className={`${msg.isUser ? "text-primary-foreground" : "text-foreground"} leading-relaxed`}>
            {msg.text}
          </P>
          <Small className={`${msg.isUser ? "text-primary-foreground/70" : "text-muted-foreground"} mt-1`}>
            {formatTime(msg.timestamp)}
          </Small>
        </View>
        {msg.isUser && (
          <View className="w-8 h-8 bg-muted rounded-full items-center justify-center ml-3">
            <Small className="text-muted-foreground font-medium">You</Small>
          </View>
        )}
      </View>
    </View>
  );

  const quickActions = [
    { label: "Portfolio",  action: () => sendToBackend("Show me my portfolio") },
    { label: "Spending",   action: () => sendToBackend("Analyze my spending") },
    { label: "Bills",      action: () => sendToBackend("Check upcoming bills") },
    { label: "Goals",      action: () => sendToBackend("Show my financial goals") },
  ];

  // PTT button appearance based on voice status
  const pttStyles = {
    idle:       { bg: "bg-primary",     label: "Tap to speak" },
    listening:  { bg: "bg-destructive", label: "Listening\u2026 (tap to stop)" },
    processing: { bg: "bg-amber-500",   label: "Thinking\u2026" },
    speaking:   { bg: "bg-emerald-500", label: "Speaking\u2026" },
  };
  const ptt = pttStyles[voiceStatus] ?? pttStyles.idle;

  const handlePTT = () => {
    if (voiceStatus === "idle")      { startListening(); return; }
    if (voiceStatus === "listening") { stopListening();  return; }
    // processing / speaking: ignore taps
  };

  const PttIcon =
    voiceStatus === "idle"       ? Mic     :
    voiceStatus === "listening"  ? MicOff  :
    voiceStatus === "processing" ? Loader2 : Volume2;

  return (
    <SafeAreaView className="flex-1 bg-background">
      <Gradient key={String(isListening)} position="top" isSpeaking={isListening} />

      {/* Header */}
      <View className="flex-row items-center justify-between px-4 py-3 border-b border-border/20">
        <H4 className="flex-1 mx-4">AI Assistant</H4>
        <View className="flex-row items-center gap-2">
          <View className={`w-2 h-2 rounded-full ${
            voiceStatus === "listening"  ? "bg-destructive" :
            voiceStatus === "processing" ? "bg-amber-500"   :
            voiceStatus === "speaking"   ? "bg-emerald-500" : "bg-success"
          }`} />
          <Small className="text-muted-foreground text-xs">{ptt.label.split("\u2026")[0].toUpperCase()}</Small>
        </View>
      </View>

      {/* Messages */}
      <ScrollView
        ref={scrollViewRef}
        className="flex-1 px-4"
        contentContainerStyle={{ paddingVertical: 20 }}
        showsVerticalScrollIndicator={false}
      >
        {messages.map(renderMessage)}
        <TypingIndicator visible={isTyping} />
        {isListening && transcript ? (
          <View className="mb-4 items-end">
            <View className="bg-destructive/10 border border-destructive/30 rounded-2xl rounded-br-sm px-4 py-3 max-w-[85%]">
              <Small className="text-destructive/80 italic">{transcript}</Small>
            </View>
          </View>
        ) : null}
      </ScrollView>

      {/* Quick actions */}
      <View className="px-4 py-3 bg-card/30 border-t border-border/20">
        <Small className="text-muted-foreground mb-2">Quick Actions:</Small>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View className="flex-row space-x-2">
            {quickActions.map((a, i) => (
              <TouchableOpacity
                key={i}
                onPress={a.action}
                disabled={isTyping}
                className="bg-muted/50 mr-2 rounded-full px-4 py-2 border border-border/30"
              >
                <Small className="text-muted-foreground">{a.label}</Small>
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>
      </View>

      {/* Push-to-Talk mic button */}
      <View className="px-4 pb-8 pt-4 bg-background border-t border-border/20 items-center gap-3">
        {/* Pulse ring while recording */}
        <View className="relative items-center justify-center">
          {isListening && (
            <View className="absolute w-28 h-28 rounded-full bg-destructive/15" />
          )}
          <TouchableOpacity
            onPress={handlePTT}
            disabled={voiceStatus === "processing" || voiceStatus === "speaking"}
            activeOpacity={0.8}
            className={`w-20 h-20 rounded-full ${ptt.bg} items-center justify-center shadow-xl`}
          >
            <PttIcon size={30} color="white" strokeWidth={2} />
          </TouchableOpacity>
        </View>

        <Small className="text-muted-foreground">{ptt.label}</Small>

        {/* Hint strip */}
        <View className="bg-amber-50 border border-amber-200 rounded-xl p-3 w-full">
          <View className="flex-row items-center mb-1">
            <Zap size={14} color="#92400e" />
            <Small className="text-amber-800 font-medium ml-1">Try saying:</Small>
          </View>
          <Small className="text-amber-700">
            "Mera portfolio dikhao" \u2022 "SIP calculate karo" \u2022 "Tax bachao"
          </Small>
        </View>
      </View>
    </SafeAreaView>
  );
}
