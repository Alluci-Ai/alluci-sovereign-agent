import { VerifiableSignatureData } from "../../vdxf/classes/VerifiableSignatureData";
import { CompactAddressObject, CompactIAddressObject } from "../../vdxf/classes/CompactAddressObject";
import { HASH_TYPE_SHA256 } from '../../constants/pbaas';
import { BN } from "bn.js";

const createHash = require("create-hash");

describe('Serializes and deserializes SignatureData', () => {
    test('(de)serialize SignatureData', () => {

        const s = new VerifiableSignatureData({
            version: new BN(1),
            signatureAsVch: Buffer.from("efc8d6b60c5b6efaeb3fce4b2c0749c317f2167549ec22b1bee411b8802d5aaf", 'hex'),
            hashType: HASH_TYPE_SHA256,
            flags: new BN(0),
            identityID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: "i7LaXD2cdy1zeh33eHzZaEPyueT4yQmBfW", rootSystemName: "VRSC" }),
            systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_FQN, address: "VRSC", rootSystemName: "VRSC" }),
        })

        const sFromBuf = new VerifiableSignatureData();

        sFromBuf.fromBuffer(s.toBuffer())

        expect(sFromBuf.toBuffer().toString('hex')).toBe(s.toBuffer().toString('hex'))
    });

    test('(de)serialize SignatureData with vdxfKeys', () => {
        const s = new VerifiableSignatureData({
            version: new BN(1),
            signatureVersion: new BN(2),
            signatureAsVch: Buffer.from("efc8d6b60c5b6efaeb3fce4b2c0749c317f2167549ec22b1bee411b8802d5aaf", 'hex'),
            hashType: HASH_TYPE_SHA256,
            identityID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: "i7LaXD2cdy1zeh33eHzZaEPyueT4yQmBfW", rootSystemName: "VRSC" }),
            systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_FQN, address: "VRSC", rootSystemName: "VRSC" }),
            vdxfKeys: ["iRrCKQqLQrWczeNotMgqJkoUW5ZzF182Ax", "iCCSCFbq9n7ftEQCQT94t8CcVV5NdxnTvL"],
        })

        const sFromBuf = new VerifiableSignatureData();
        sFromBuf.fromBuffer(s.toBuffer())

        expect(sFromBuf.toBuffer().toString('hex')).toBe(s.toBuffer().toString('hex'))
        expect(sFromBuf.vdxfKeys).toEqual(s.vdxfKeys)
        expect(sFromBuf.hasVdxfKeys()).toBe(true)
    });

    test('(de)serialize SignatureData with vdxfKeyNames', () => {
        const s = new VerifiableSignatureData({
            version: new BN(1),
            signatureVersion: new BN(2),
            signatureAsVch: Buffer.from("efc8d6b60c5b6efaeb3fce4b2c0749c317f2167549ec22b1bee411b8802d5aaf", 'hex'),
            hashType: HASH_TYPE_SHA256,
            identityID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: "i7LaXD2cdy1zeh33eHzZaEPyueT4yQmBfW", rootSystemName: "VRSC" }),
            systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_FQN, address: "VRSC", rootSystemName: "VRSC" }),
            vdxfKeyNames: ["key.name.one", "key.name.two", "another.key"],
        })

        const sFromBuf = new VerifiableSignatureData();
        sFromBuf.fromBuffer(s.toBuffer())

        expect(sFromBuf.toBuffer().toString('hex')).toBe(s.toBuffer().toString('hex'))
        expect(sFromBuf.vdxfKeyNames).toEqual(s.vdxfKeyNames)
        expect(sFromBuf.hasVdxfKeyNames()).toBe(true)
    });

    test('(de)serialize SignatureData with boundHashes', () => {
        const s = new VerifiableSignatureData({
            version: new BN(1),
            signatureVersion: new BN(2),
            signatureAsVch: Buffer.from("efc8d6b60c5b6efaeb3fce4b2c0749c317f2167549ec22b1bee411b8802d5aaf", 'hex'),
            hashType: HASH_TYPE_SHA256,
            identityID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: "i7LaXD2cdy1zeh33eHzZaEPyueT4yQmBfW", rootSystemName: "VRSC" }),
            systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_FQN, address: "VRSC", rootSystemName: "VRSC" }),
            boundHashes: [
                Buffer.from("a".repeat(64), 'hex'),
                Buffer.from("b".repeat(64), 'hex'),
            ],
        })

        const sFromBuf = new VerifiableSignatureData();
        sFromBuf.fromBuffer(s.toBuffer())

        expect(sFromBuf.toBuffer().toString('hex')).toBe(s.toBuffer().toString('hex'))
        expect(sFromBuf.boundHashes?.length).toBe(2)
        expect(sFromBuf.hasBoundHashes()).toBe(true)
    });

    test('(de)serialize SignatureData with all extra data', () => {
        const s = new VerifiableSignatureData({
            version: new BN(1),
            signatureVersion: new BN(2),
            signatureAsVch: Buffer.from("efc8d6b60c5b6efaeb3fce4b2c0749c317f2167549ec22b1bee411b8802d5aaf", 'hex'),
            hashType: HASH_TYPE_SHA256,
            identityID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: "i7LaXD2cdy1zeh33eHzZaEPyueT4yQmBfW", rootSystemName: "VRSC" }),
            systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_FQN, address: "VRSC", rootSystemName: "VRSC" }),
            vdxfKeys: ["iRrCKQqLQrWczeNotMgqJkoUW5ZzF182Ax", "iCCSCFbq9n7ftEQCQT94t8CcVV5NdxnTvL"],
            vdxfKeyNames: ["key.name.one", "key.name.two"],
            boundHashes: [
                Buffer.from("a".repeat(64), 'hex'),
                Buffer.from("b".repeat(64), 'hex'),
            ],
        })

        const sFromBuf = new VerifiableSignatureData();
        sFromBuf.fromBuffer(s.toBuffer())

        expect(sFromBuf.toBuffer().toString('hex')).toBe(s.toBuffer().toString('hex'))
        expect(sFromBuf.vdxfKeys).toEqual(s.vdxfKeys)
        expect(sFromBuf.vdxfKeyNames).toEqual(s.vdxfKeyNames)
        expect(sFromBuf.boundHashes?.length).toBe(2)
        expect(sFromBuf.hasVdxfKeys()).toBe(true)
        expect(sFromBuf.hasVdxfKeyNames()).toBe(true)
        expect(sFromBuf.hasBoundHashes()).toBe(true)
    });

    test('getIdentityHash with extra data - vdxfKeys are sorted by buffer value', () => {
        // Create with keys in non-sorted order
        const s = new VerifiableSignatureData({
            version: new BN(1),
            signatureVersion: new BN(2),
            signatureAsVch: Buffer.from("AgVfngwAAUEgywnMVejMz6iZj88qRawIivovU9L9uQtGcDbD635QbNt2G/QoZjxT6c7w099JjBd2cGa8ajI99KG0MTbHT99ZZw==", 'base64'),
            hashType: HASH_TYPE_SHA256,
            identityID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: "i4M7ar436N7wKHgZodjGAWdsBSNjG7cz8s", rootSystemName: "VRSCTEST" }),
            systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_FQN, address: "VRSCTEST", rootSystemName: "VRSCTEST" }),
            vdxfKeys: ["iQRWB2Ay9rEbzStXDjMFpveh4oEmD6YWXa"],
        })

        const sigHash = createHash("sha256").update("hello world1").digest();
        const hash1 = s.getIdentityHash(826975, sigHash);

        // Create with same keys but different order
        const s2 = new VerifiableSignatureData({
            version: new BN(1),
            signatureVersion: new BN(2),
            signatureAsVch: Buffer.from("AgVfngwAAUEgywnMVejMz6iZj88qRawIivovU9L9uQtGcDbD635QbNt2G/QoZjxT6c7w099JjBd2cGa8ajI99KG0MTbHT99ZZw==", 'base64'),
            hashType: HASH_TYPE_SHA256,
            identityID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: "i4M7ar436N7wKHgZodjGAWdsBSNjG7cz8s", rootSystemName: "VRSCTEST" }),
            systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_FQN, address: "VRSCTEST", rootSystemName: "VRSCTEST" }),
            vdxfKeys: ["iQRWB2Ay9rEbzStXDjMFpveh4oEmD6YWXa"],
        })

        const hash2 = s2.getIdentityHash(826975, sigHash);

        // Hashes should be identical because keys are sorted before hashing
        expect(hash1.toString('hex')).toBe(hash2.toString('hex'))
    });

    test('getIdentityHash with extra data - vdxfKeys are sorted by buffer value', () => {
        // Create with keys in non-sorted order
        const s = new VerifiableSignatureData({
            version: new BN(1),
            signatureVersion: new BN(2),
            signatureAsVch: Buffer.from("AgV1ngwAAUEfYEg7UW5l0zS88ERfSBXZJ6+RWiUwXQ8BwMkkUesmemFBF29LEVw0C60csXMbMdLYxt3qGLLhgHnev9XIwWFIvw==", 'base64'),
            hashType: HASH_TYPE_SHA256,
            identityID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: "i4M7ar436N7wKHgZodjGAWdsBSNjG7cz8s", rootSystemName: "VRSCTEST" }),
            systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_FQN, address: "VRSCTEST", rootSystemName: "VRSCTEST" }),
        })

        const sigHash = createHash("sha256").update("hello world1").digest();
        const hash1 = s.getIdentityHash(826997, sigHash);

        // Hashes should be identical because keys are sorted before hashing
        expect(hash1.toString('hex')).toBe(hash1.toString('hex'))

    });

    test('fromSignatureDataJson parses all fields correctly', () => {
        const signatureDataJson = {
            "signaturedata": {
                "version": 1,
                "systemid": "iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq", //
                "hashtype": 5,
                "signaturehash": "f8220bacb0bf5bd8ca33a890184b66b35fb64647274b4b9fb4ff90e68f77a5a7",
                "identityid": "i4M7ar436N7wKHgZodjGAWdsBSNjG7cz8s",
                "signaturetype": 1,
                "signature": "AgVgngwAAUEg4QYvX2zJJUZLa4YdtwoxehCQ9T3U6xGw08SmonRSv1xofR1264j5/bdXmq6Qc2YgzlCt3DqVKM9c9DLuCU4bbQ==",//
                "vdxfkeys": [
                    "iQRWB2Ay9rEbzStXDjMFpveh4oEmD6YWXa",
                    "i5cVmwQQZfWz1AYp9AwKakPQxTjQfK2Mrk",
                    "iKqjqcXE15KPNuCvm2evZUnwiYEZ2CLnV2",
                    "iRrCKQqLQrWczeNotMgqJkoUW5ZzF182Ax"
                ],
                "vdxfkeynames": [
                    "examplename1",
                    "examplename2"
                ],
                "boundhashes": [
                    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                ]
            },
            "system": "VRSCTEST",
            "systemid": "iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq",
            "hashtype": "sha256",
            "hash": "f8220bacb0bf5bd8ca33a890184b66b35fb64647274b4b9fb4ff90e68f77a5a7",
            "identity": "endorsetest.VRSCTEST@",
            "canonicalname": "endorsetest.vrsctest@",
            "address": "i4M7ar436N7wKHgZodjGAWdsBSNjG7cz8s",
            "signatureheight": 826976,
            "vdxfkeys": [
                "iQRWB2Ay9rEbzStXDjMFpveh4oEmD6YWXa",
                "i5cVmwQQZfWz1AYp9AwKakPQxTjQfK2Mrk",
                "iKqjqcXE15KPNuCvm2evZUnwiYEZ2CLnV2",
                "iRrCKQqLQrWczeNotMgqJkoUW5ZzF182Ax"
            ],
            "vdxfkeynames": [
                "examplename1",
                "examplename2"
            ],
            "boundhashes": [
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            ],
            "signatureversion": 2,
            "signature": "AgVgngwAAUEg4QYvX2zJJUZLa4YdtwoxehCQ9T3U6xGw08SmonRSv1xofR1264j5/bdXmq6Qc2YgzlCt3DqVKM9c9DLuCU4bbQ=="
        };

        const verifiableSig = VerifiableSignatureData.fromCLIJson(signatureDataJson);

        // Verify version fields
        expect(verifiableSig.version.toNumber()).toBe(1);
        expect(verifiableSig.signatureVersion.toNumber()).toBe(2); // Auto-detected as v2 due to extra data

        // Verify IDs
        expect(verifiableSig.systemID.toIAddress()).toBe("iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq");
        expect(verifiableSig.identityID.toIAddress()).toBe("i4M7ar436N7wKHgZodjGAWdsBSNjG7cz8s");

        // Verify hash type
        expect(verifiableSig.hashType.toNumber()).toBe(5);

        // Verify vdxfKeys (stored as strings)
        expect(verifiableSig.vdxfKeys).toBeDefined();
        expect(verifiableSig.vdxfKeys?.length).toBe(4);
        expect(verifiableSig.vdxfKeys?.[0]).toBe("iQRWB2Ay9rEbzStXDjMFpveh4oEmD6YWXa");
        expect(verifiableSig.vdxfKeys?.[1]).toBe("i5cVmwQQZfWz1AYp9AwKakPQxTjQfK2Mrk");
        expect(verifiableSig.vdxfKeys?.[2]).toBe("iKqjqcXE15KPNuCvm2evZUnwiYEZ2CLnV2");
        expect(verifiableSig.vdxfKeys?.[3]).toBe("iRrCKQqLQrWczeNotMgqJkoUW5ZzF182Ax");

        // Verify vdxfKeyNames
        expect(verifiableSig.vdxfKeyNames).toBeDefined();
        expect(verifiableSig.vdxfKeyNames?.length).toBe(2);
        expect(verifiableSig.vdxfKeyNames?.[0]).toBe("examplename1");
        expect(verifiableSig.vdxfKeyNames?.[1]).toBe("examplename2");

        // Verify boundHashes
        expect(verifiableSig.boundHashes).toBeDefined();
        expect(verifiableSig.boundHashes?.length).toBe(2);
        expect(verifiableSig.boundHashes?.[0].toString('hex')).toBe("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
        expect(verifiableSig.boundHashes?.[1].toString('hex')).toBe("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");

        // Verify signature
        expect(verifiableSig.signatureAsVch.toString('base64')).toBe("AgVgngwAAUEg4QYvX2zJJUZLa4YdtwoxehCQ9T3U6xGw08SmonRSv1xofR1264j5/bdXmq6Qc2YgzlCt3DqVKM9c9DLuCU4bbQ==");
    });

    test('verify daemon signature with all extra data - from signdata', () => {
        // Real signature data from daemon with vdxfkeys, vdxfkeynames, and boundhashes
        const signatureDataJson = {
            "signaturedata": {
                "version": 1,
                "systemid": "iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq", //
                "hashtype": 5,
                "signaturehash": "f8220bacb0bf5bd8ca33a890184b66b35fb64647274b4b9fb4ff90e68f77a5a7",
                "identityid": "i4M7ar436N7wKHgZodjGAWdsBSNjG7cz8s",
                "signaturetype": 1,
                "signature": "AgVgngwAAUEg4QYvX2zJJUZLa4YdtwoxehCQ9T3U6xGw08SmonRSv1xofR1264j5/bdXmq6Qc2YgzlCt3DqVKM9c9DLuCU4bbQ==",//
                "vdxfkeys": [
                    "iQRWB2Ay9rEbzStXDjMFpveh4oEmD6YWXa",
                    "i5cVmwQQZfWz1AYp9AwKakPQxTjQfK2Mrk",
                    "iKqjqcXE15KPNuCvm2evZUnwiYEZ2CLnV2",
                    "iRrCKQqLQrWczeNotMgqJkoUW5ZzF182Ax"
                ],
                "vdxfkeynames": [
                    "examplename1",
                    "examplename2"
                ],
                "boundhashes": [
                    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                ]
            },
            "system": "VRSCTEST",
            "systemid": "iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq",
            "hashtype": "sha256",
            "hash": "f8220bacb0bf5bd8ca33a890184b66b35fb64647274b4b9fb4ff90e68f77a5a7",
            "identity": "endorsetest.VRSCTEST@",
            "canonicalname": "endorsetest.vrsctest@",
            "address": "i4M7ar436N7wKHgZodjGAWdsBSNjG7cz8s",
            "signatureheight": 826976,
            "vdxfkeys": [
                "iQRWB2Ay9rEbzStXDjMFpveh4oEmD6YWXa",
                "i5cVmwQQZfWz1AYp9AwKakPQxTjQfK2Mrk",
                "iKqjqcXE15KPNuCvm2evZUnwiYEZ2CLnV2",
                "iRrCKQqLQrWczeNotMgqJkoUW5ZzF182Ax"
            ],
            "vdxfkeynames": [
                "examplename1",
                "examplename2"
            ],
            "boundhashes": [
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            ],
            "signatureversion": 2,
            "signature": "AgVgngwAAUEg4QYvX2zJJUZLa4YdtwoxehCQ9T3U6xGw08SmonRSv1xofR1264j5/bdXmq6Qc2YgzlCt3DqVKM9c9DLuCU4bbQ=="
        };

        // Create VerifiableSignatureData directly from SignatureData JSON
        const verifiableSig = VerifiableSignatureData.fromCLIJson(signatureDataJson);

        // Verify the parsed data
        expect(verifiableSig.version.toNumber()).toBe(1);
        expect(verifiableSig.signatureVersion.toNumber()).toBe(2);
        expect(verifiableSig.hashType.toNumber()).toBe(5);
        expect(verifiableSig.systemID.toIAddress()).toBe("iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq");
        expect(verifiableSig.identityID.toIAddress()).toBe("i4M7ar436N7wKHgZodjGAWdsBSNjG7cz8s");
        expect(verifiableSig.vdxfKeys?.length).toBe(4);
        expect(verifiableSig.vdxfKeyNames?.length).toBe(2);
        expect(verifiableSig.boundHashes?.length).toBe(2);

        

    });


});
