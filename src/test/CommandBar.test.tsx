import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CommandBar from '../../features/terminal/CommandBar';
import React from 'react';

// Mock hooks and store
vi.mock('../../hooks/useVoice', () => ({
  useVoice: () => ({
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
  }),
}));

vi.mock('../../store/useStore', () => ({
  useStore: vi.fn((selector) => selector({ isVoiceRecording: false })),
}));

describe('CommandBar Component', () => {
  const mockSetTextInput = vi.fn();
  const mockRemoveAttachment = vi.fn();
  const mockHandleFileChange = vi.fn();
  const mockHandleCommandSubmit = vi.fn();
  const mockHandlePaste = vi.fn();
  const fileInputRef = { current: null } as any;

  const defaultProps = {
    textInput: '',
    setTextInput: mockSetTextInput,
    attachments: [],
    removeAttachment: mockRemoveAttachment,
    fileInputRef,
    handleFileChange: mockHandleFileChange,
    handleCommandSubmit: mockHandleCommandSubmit,
    handlePaste: mockHandlePaste,
    isProcessing: false,
  };

  it('renders input and action buttons', () => {
    render(<CommandBar {...defaultProps} />);
    expect(screen.getByPlaceholderText(/Ask Alluci/i)).toBeInTheDocument();
    expect(screen.getByTitle(/Ingest Data/i)).toBeInTheDocument();
    expect(screen.getByTitle(/Hold to Speak/i)).toBeInTheDocument();
  });

  it('updates text input on change', () => {
    render(<CommandBar {...defaultProps} />);
    const input = screen.getByPlaceholderText(/Ask Alluci/i);
    fireEvent.change(input, { target: { value: 'Hello Alluci' } });
    expect(mockSetTextInput).toHaveBeenCalledWith('Hello Alluci');
  });

  it('renders attachments and allows removal', () => {
    const props = {
        ...defaultProps,
        attachments: [{ name: 'test.pdf', mimeType: 'application/pdf' }]
    };
    render(<CommandBar {...props} />);
    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    
    const removeBtn = screen.getByText('✕');
    fireEvent.click(removeBtn);
    expect(mockRemoveAttachment).toHaveBeenCalledWith(0);
  });

  it('shows processing state in submit button', () => {
    render(<CommandBar {...defaultProps} isProcessing={true} />);
    expect(screen.getByText('+')).toBeInTheDocument(); // Spinner fallback in mock
    expect(screen.getByPlaceholderText(/Adding to replay queue/i)).toBeInTheDocument();
  });
});
