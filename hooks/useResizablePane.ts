
import { useState, useCallback, useEffect } from 'react';

export const useResizablePane = (storageKey: string, initialWidth: number = 400) => {
  const [width, setWidth] = useState(parseInt(localStorage.getItem(storageKey) || initialWidth.toString()));
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth > 320 && newWidth < 800) {
        setWidth(newWidth);
      }
    };
    const handleMouseUp = () => {
      setIsResizing(false);
      localStorage.setItem(storageKey, width.toString());
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, width, storageKey]);

  return {
    width,
    isResizing,
    startResizing
  };
};
