'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Zap, CreditCard, Shield, Sparkles } from 'lucide-react';
import { StoryItem } from '@/lib/neobank/types';
import StoryViewerModal from './StoryViewerModal';

export const DEFAULT_STORIES: StoryItem[] = [
  {
    id: 'story-vaults',
    tag: 'Treasury & APY',
    title: '4.85% APY Vaults',
    subtitle: 'High-Yield Savings',
    gradient: 'from-emerald-900/90 via-slate-900/95 to-slate-950',
    icon: 'TrendingUp',
    actionText: 'Explore Savings Vaults',
    actionType: 'savings',
    content: {
      headline: 'Earn 4.85% APY with KarinBank Savings Vaults',
      details: 'Maximize your idle cash with daily compounding interest, zero maintenance fees, and instant transfer flexibility.',
      highlightMetric: '4.85% APY',
      metricLabel: 'Current Annual Yield',
      bullets: [
        'Daily compounding interest deposited monthly',
        'No lock-in periods or withdrawal penalties',
        'Directly linked to your primary checking balance',
      ],
    },
  },
  {
    id: 'story-fednow',
    tag: 'Federal Reserve',
    title: 'FedNow 24/7/365',
    subtitle: 'Instant Clearance',
    gradient: 'from-indigo-900/90 via-slate-900/95 to-slate-950',
    icon: 'Zap',
    actionText: 'Send Instant Payment',
    actionType: 'transfer',
    content: {
      headline: 'Instant 24/7 Clearance via Federal Reserve FedNow',
      details: 'Experience zero-wait interbank settlement even on weekends and bank holidays with institutional security.',
      highlightMetric: '< 2.5s',
      metricLabel: 'Average Settlement Time',
      bullets: [
        'Clears 24 hours a day, 365 days a year',
        'Zero transfer fees on all consumer accounts',
        'Real-time ISO 20022 confirmation messages',
      ],
    },
  },
  {
    id: 'story-cashback',
    tag: 'Rewards',
    title: '3% Smart Cashback',
    subtitle: 'Dining & Transit',
    gradient: 'from-purple-900/90 via-slate-900/95 to-slate-950',
    icon: 'CreditCard',
    actionText: 'View Cashback Categories',
    actionType: 'cashback',
    content: {
      headline: 'Automated 3% Cashback on Your Daily Expenses',
      details: 'Earn cash back directly into your high-yield vault every time you use your KarinBank Black Platinum card.',
      highlightMetric: '3.0%',
      metricLabel: 'Top Tier Category Return',
      bullets: [
        '3% on restaurants, coffee shops & delivery',
        '2% on groceries, utilities & transit',
        '1% unlimited on all other eligible card purchases',
      ],
    },
  },
  {
    id: 'story-fdic',
    tag: 'Security',
    title: 'FDIC Insured',
    subtitle: 'Up to $250,000',
    gradient: 'from-blue-900/90 via-slate-900/95 to-slate-950',
    icon: 'Shield',
    actionText: 'Review Security Controls',
    actionType: 'security',
    content: {
      headline: 'Your Deposits Are Fully Insured & Protected',
      details: 'Rest easy knowing all USD deposits are backed by the full faith of the United States Federal Reserve System.',
      highlightMetric: '$250,000',
      metricLabel: 'Standard FDIC Coverage Limit',
      bullets: [
        'End-to-end cryptographic transaction signing',
        '24/7 AI-driven behavioral fraud monitoring',
        'Instant biometric lock & disposable virtual cards',
      ],
    },
  },
  {
    id: 'story-pulse',
    tag: 'Analytics',
    title: 'Weekly Financial Pulse',
    subtitle: 'Real-time Insights',
    gradient: 'from-slate-800/90 via-slate-900/95 to-slate-950',
    icon: 'Sparkles',
    actionText: 'Open Analytics Studio',
    actionType: 'analytics',
    content: {
      headline: 'Deep Cashflow Telemetry Powered by ClickHouse',
      details: 'Gain unprecedented visibility into your income, burn rate, recurring bills, and merchant spending patterns.',
      highlightMetric: '-14%',
      metricLabel: 'Discretionary Spend vs Last Week',
      bullets: [
        'Automated categorization across 14 spending sectors',
        'Predictive balance forecasting based on recurring debits',
        'Exportable statements and tax-ready CSV summaries',
      ],
    },
  },
];

interface StoriesBarProps {
  stories?: StoryItem[];
  onActionClick?: (actionType: string) => void;
}

export default function StoriesBar({ stories = DEFAULT_STORIES, onActionClick }: StoriesBarProps) {
  const [selectedStory, setSelectedStory] = useState<StoryItem | null>(null);

  const getStoryIcon = (iconName: string) => {
    switch (iconName) {
      case 'TrendingUp':
        return <TrendingUp className="w-4 h-4 text-emerald-400" />;
      case 'Zap':
        return <Zap className="w-4 h-4 text-emerald-300" />;
      case 'CreditCard':
        return <CreditCard className="w-4 h-4 text-purple-400" />;
      case 'Shield':
        return <Shield className="w-4 h-4 text-blue-400" />;
      default:
        return <Sparkles className="w-4 h-4 text-indigo-400" />;
    }
  };

  return (
    <div className="w-full">
      {/* Horizontal Stories Carousel */}
      <div className="flex items-center gap-3.5 overflow-x-auto no-scrollbar py-2 px-1">
        {stories.map((story) => (
          <motion.button
            key={story.id}
            whileHover={{ scale: 1.03, y: -2 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => setSelectedStory(story)}
            className="flex-shrink-0 flex items-center gap-3 p-2.5 pr-4 rounded-2xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-purple-500/40 backdrop-blur-xl transition-all shadow-lg text-left group"
          >
            {/* Story Gradient Ring & Icon */}
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-white/15 flex items-center justify-center flex-shrink-0 group-hover:border-purple-400/50 transition-all">
              {getStoryIcon(story.icon)}
            </div>

            {/* Story Titles */}
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-bold text-white/40 tracking-wider">
                {story.tag}
              </span>
              <span className="text-xs font-bold text-white group-hover:text-purple-300 transition-colors whitespace-nowrap">
                {story.title}
              </span>
            </div>
          </motion.button>
        ))}
      </div>

      {/* Stories Viewer Modal */}
      <StoryViewerModal
        story={selectedStory}
        allStories={stories}
        isOpen={!!selectedStory}
        onClose={() => setSelectedStory(null)}
        onSelectStory={(s) => setSelectedStory(s)}
        onActionClick={onActionClick}
      />
    </div>
  );
}
