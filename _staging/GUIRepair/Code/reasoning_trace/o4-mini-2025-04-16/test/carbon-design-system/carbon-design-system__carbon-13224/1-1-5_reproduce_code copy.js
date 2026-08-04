import React, { useState, useRef } from 'react';
import {
  Button,
  IconButton,
  Menu,
  MenuItem,
} from '@carbon/react';
import { ChevronDown, ChevronUp } from '@carbon/icons-react';

function ComboButton({ items, onPrimaryClick }) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef(null);

  const handleToggle = () => {
    setOpen(!open);
  };
  const handleClose = () => {
    setOpen(false);
  };

  // compute x/y from triggerRef to position the menu
  const rect = triggerRef.current?.getBoundingClientRect() || { x: 0, y: 0, width: 0, height: 0 };
  const menuProps = {
    open,
    onClose: handleClose,
    x: [rect.x, rect.x + rect.width],
    y: rect.y + rect.height,
  };

  return (
    <div ref={triggerRef} style={{ display: 'inline-flex', position: 'relative' }}>
      <Button onClick={onPrimaryClick}>Button</Button>
      <IconButton
        kind="ghost"
        onClick={handleToggle}
        renderIcon={open ? ChevronUp : ChevronDown}
        iconDescription="Show menu"
        tooltipPosition="bottom"
      />
      <Menu {...menuProps}>
        {items.map((item) => (
          <MenuItem
            key={item.id}
            label={item.label}
            onClick={() => {
              console.log('Selected', item);
              handleClose();
            }}
          />
        ))}
      </Menu>
    </div>
  );
}

export default function App() {
  const options = [
    { id: 'opt-2', label: 'Second option' },
    { id: 'opt-3', label: 'Third option' },
    { id: 'opt-4', label: 'Fourth option' },
  ];
  return (
    <div style={{ padding: '2rem', background: '#161616', height: '100vh' }}>
      <ComboButton items={options} onPrimaryClick={() => alert('Primary action')} />
    </div>
  );
}