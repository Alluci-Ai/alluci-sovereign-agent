import React from 'react';
import { Connection } from '../../../types';
import { SharedModalShell } from './SharedModalShell';
import { VerusIdLogin } from '../../bridges/VerusIdLogin';

export const VerusIdentityModal: React.FC<{
    connection: Connection;
    onComplete: (session: string, img: string) => void;
    onCancel: () => void;
}> = ({ connection, onComplete, onCancel }) => {
    return (
        <SharedModalShell connection={connection} title="VERUSID_SOVEREIGN_LINK" onCancel={onCancel}>
            <VerusIdLogin
                onComplete={(identity) => onComplete(`verus_${identity}`, `https://api.dicebear.com/7.x/identicon/svg?seed=${identity}`)}
                onCancel={onCancel}
            />
        </SharedModalShell>
    );
};
