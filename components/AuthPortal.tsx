import React from 'react';
import { Connection } from '../types';
import { OAuthModal } from '../features/channels/auth/OAuthModal';
import { TokenModal } from '../features/channels/auth/TokenModal';
import { QRSyncModal } from '../features/channels/auth/QRSyncModal';
import { SecureTunnelModal } from '../features/channels/auth/SecureTunnelModal';
import { WebSessionModal } from '../features/channels/auth/WebSessionModal';
import { VerusIdentityModal } from '../features/channels/auth/VerusIdentityModal';

export const AuthPortal: React.FC<{
    connection: Connection;
    onComplete: (session: string, img: string) => void;
    onCancel: () => void;
}> = (props) => {
    switch (props.connection.authType) {
        case 'OAUTH2':
            return <OAuthModal {...props} />;
        case 'TOKEN':
            return <TokenModal {...props} />;
        case 'QR_SYNC':
            return <QRSyncModal {...props} />;
        case 'SECURE_TUNNEL':
            return <SecureTunnelModal {...props} />;
        case 'WEB_SESSION':
            return <WebSessionModal {...props} />;
        case 'IDENTITY_LINK':
            return <VerusIdentityModal {...props} />;
        default:
            return null;
    }
};
